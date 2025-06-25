import os
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np

router = APIRouter()

# 1. SETUP: Define date variables for file naming
today = datetime.now()
year = str(today.year)
month = str(today.month)
day = str(today.day)

# 2. STEP: Get the root directory of your project (where this .py file lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 3. STEP: Define the path to your data folder (put all Excel files here)
#    - Make sure you have a folder named "MachinePulseData" in your project directory
MACHINES_BASE_PATH = os.path.join(PROJECT_ROOT, "machine")

# 4. STEP: Define the path to your master Excel file
#    - Place your "MachinePulse_All_Machines.xlsx" inside "MachinePulseData"
all_machines_path = os.path.join(MACHINES_BASE_PATH, "MachinePulse_All_Machines")

# 5. STEP: Define the path for warnings Excel file
#    - Use "/tmp" for writing files on Render (it's always writable)
warning_excel_path = os.path.join("/tmp", f"warnings_{year}_{month}_{day}.xlsx")

# 6. STEP: Load your master Excel file at startup
#    - If the file doesn't exist, create an empty DataFrame to avoid crashes
if os.path.exists(all_machines_path):
    all_machines_df = pd.read_excel(all_machines_path)
else:
    all_machines_df = pd.DataFrame()

# 7. APIs

@router.get("/machines")
def list_machines():
    data = all_machines_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/operational_machines")
def list_operational_machines():
    operational_df = all_machines_df[all_machines_df['MachineStatus'] == 'Operational']
    data = operational_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/non_operational_machines")
def list_non_operational_machines():
    non_operational_df = all_machines_df[all_machines_df['MachineStatus'] == 'Non_Operational']
    data = non_operational_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/machines_with_alerts_count")
def get_warnings_count():
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})
    else:
        warning_df = pd.read_excel(warning_excel_path)
        warning_df = warning_df[['PlantID', 'ShopID', 'MachineID', 'Machine','Timestamp','Part','Value','Part', 'Status']].copy()
        warning_df.drop_duplicates(inplace=True)
        return warning_df.to_dict(orient='records')

@router.get("/machines_with_warnings")
def get_machines_with_warnings():
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})

    try:
        df = pd.read_excel(warning_excel_path)
        required_columns = {'PlantID', 'ShopID', 'MachineID', 'Machine', 'Status'}
        if not required_columns.issubset(df.columns):
            return JSONResponse(
                status_code=400,
                content={"error": f"Excel file must contain columns: {', '.join(required_columns)}"}
            )
        unique_rows = df[list(required_columns)].drop_duplicates()
        return JSONResponse(content={
            "machines_with_warnings": unique_rows.to_dict(orient='records')
        })
    except Exception as e:
        logging.error(f"Failed to process warning Excel: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/risk/{category}")
def get_rows_by_risk_category(category: str = Path(..., description="Risk category to filter by")):
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})

    try:
        df = pd.read_excel(warning_excel_path)
        if 'RiskCategory' not in df.columns:
            return JSONResponse(status_code=400, content={"error": "Excel file missing 'RiskCategory' column."})

        filtered_df = df[df['RiskCategory'].str.lower() == category.lower()]
        if filtered_df.empty:
            return JSONResponse(content={"message": f"No rows found for risk category '{category}'", "data": []})

        return JSONResponse(content={"data": filtered_df.to_dict(orient='records')})

    except Exception as e:
        logging.error(f"Failed to filter by risk category {category}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/risk_highest")
def get_highest_risks():
    return get_rows_by_risk_category("Highest Risk")

@router.get("/risk_high")
def get_high_risks():
    return get_rows_by_risk_category("High Risk")

@router.get("/risk_medium")
def get_medium_risks():
    return get_rows_by_risk_category("Medium Risk")

@router.get("/risk_low")
def get_low_risks():
    return get_rows_by_risk_category("Low Risk")

# 8. Background task to scan Excel files every 60 seconds and update warnings

async def scan_files_for_warnings():
    while True:
        logging.info("Scanning Excel files for warnings...")
        warnings_list = []
        try:
            # STEP: List all machine directories inside MachinePulseData
            machine_dirs = [name for name in os.listdir(MACHINES_BASE_PATH)
                            if os.path.isdir(os.path.join(MACHINES_BASE_PATH, name))]

            for machine in machine_dirs:
                machine_path = os.path.join(MACHINES_BASE_PATH, machine, year, month, day)
                excel_file = os.path.join(machine_path, f"{machine}.xlsx")

                if not os.path.exists(excel_file):
                    logging.debug(f"No Excel file found for {machine}")
                    continue

                df = pd.read_excel(excel_file)

                required_columns = {'PlantID', 'ShopID', 'Machine', 'MachineID', 'Timestamp', 'Part', 'Value', 'Unit'}
                if not required_columns.issubset(df.columns):
                    logging.warning(f"Missing columns in {excel_file}")
                    continue

                cond = ((df['Unit'] == 'mm/sec') & (df['Value'] > 8)) | \
                       ((df['Unit'] == 'Degree C') & (df['Value'] > 70))
                warning_rows = df.loc[cond, ['PlantID', 'ShopID', 'Machine', 'MachineID', 'Timestamp', 'Part', 'Value', 'Unit']].copy()
                warning_rows['Status'] = 'Warning'

                # Risk Category for vibration levels
                warning_rows['RiskCategory'] = 'NA'
                mask = warning_rows['Unit'] == 'mm/sec'
                warning_rows.loc[mask, 'RiskCategory'] = np.where(warning_rows.loc[mask, 'Value'] < 8, 'No Risk',
                                                            np.where(
                                                                warning_rows.loc[mask, 'Value'] < 10, 'Low Risk',
                                                                np.where(
                                                                    warning_rows.loc[mask, 'Value'] < 13, 'Medium Risk',
                                                                    np.where(
                                                                        warning_rows.loc[mask, 'Value'] < 15, 'High Risk',
                                                                        'Highest Risk'
                                                                    )
                                                                )
                                                            )
                                                        )

                warnings_list.extend(warning_rows.to_dict(orient='records'))

                # Save/append warnings Excel file to /tmp
                try:
                    warnings_df = warning_rows.copy()
                    if os.path.exists(warning_excel_path):
                        existing_df = pd.read_excel(warning_excel_path).copy()
                        combined_df = pd.concat([existing_df, warnings_df], ignore_index=True)
                        combined_df.drop_duplicates(subset=["Machine", "Timestamp", "Part"], inplace=True)
                    else:
                        combined_df = warnings_df

                    combined_df.to_excel(warning_excel_path, index=False, engine='openpyxl')
                    logging.info(f"Appended warnings to Excel: {warning_excel_path}")
                except Exception as e:
                    logging.error(f"Error writing warnings to Excel: {e}")

            logging.info(f"Warnings found: {len(warnings_list)}")
        except Exception as e:
            logging.error(f"Exception in warning scan: {e}")

        global warnings_cache
        warnings_cache = warnings_list
        await asyncio.sleep(60)

# 9. Start background scanning on app startup
@router.on_event("startup")
async def startup_event():
    asyncio.create_task(scan_files_for_warnings())

'''
import os
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np

router = APIRouter()

# Global vars to keep warnings cache and date info
warnings_cache = []
today = datetime.now()
year = str(today.year)
month = str(today.month)
day = str(today.day)

# Define base paths (relative and Linux-compatible)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MACHINES_BASE_PATH = os.path.join(PROJECT_ROOT, "MachinePulseData")

# Warnings Excel files are written to /tmp (writable on Render)
WARNING_EXCEL_DIR = "/tmp"
warning_excel_path = os.path.join(WARNING_EXCEL_DIR, f"warnings_{year}_{month}_{day}.xlsx")

# Ensure the warnings directory exists
os.makedirs(WARNING_EXCEL_DIR, exist_ok=True)

# Load the master machine list at startup
all_machines_path = os.path.join(MACHINES_BASE_PATH, "MachinePulse_All_Machines.xlsx")
if os.path.exists(all_machines_path):
    all_machines_df = pd.read_excel(all_machines_path)
else:
    all_machines_df = pd.DataFrame()  # fallback if file missing

@router.get("/machines")
def list_machines():
    data = all_machines_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/operational_machines")
def list_operational_machines():
    operational_df = all_machines_df[all_machines_df['MachineStatus'] == 'Operational']
    data = operational_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/non_operational_machines")
def list_non_operational_machines():
    non_operational_df = all_machines_df[all_machines_df['MachineStatus'] == 'Non_Operational']
    data = non_operational_df.to_dict(orient="records")
    return JSONResponse(content=data)

@router.get("/machines_with_alerts_count")
def get_warnings_count():
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})
    else:
        warning_df = pd.read_excel(warning_excel_path)
        warning_df = warning_df[['PlantID', 'ShopID', 'MachineID', 'Machine','Timestamp','Part','Value','Part', 'Status']].copy()
        warning_df.drop_duplicates(inplace=True)
        return warning_df.to_dict(orient='records')

@router.get("/machines_with_warnings")
def get_machines_with_warnings():
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})

    try:
        df = pd.read_excel(warning_excel_path)
        required_columns = {'PlantID', 'ShopID', 'MachineID', 'Machine', 'Status'}
        if not required_columns.issubset(df.columns):
            return JSONResponse(
                status_code=400,
                content={"error": f"Excel file must contain columns: {', '.join(required_columns)}"}
            )
        unique_rows = df[list(required_columns)].drop_duplicates()
        return JSONResponse(content={
            "machines_with_warnings": unique_rows.to_dict(orient='records')
        })
    except Exception as e:
        logging.error(f"Failed to process warning Excel: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/risk/{category}")
def get_rows_by_risk_category(category: str = Path(..., description="Risk category to filter by")):
    if not os.path.exists(warning_excel_path):
        return JSONResponse(status_code=404, content={"error": "Warnings Excel file not found."})

    try:
        df = pd.read_excel(warning_excel_path)
        if 'RiskCategory' not in df.columns:
            return JSONResponse(status_code=400, content={"error": "Excel file missing 'RiskCategory' column."})

        filtered_df = df[df['RiskCategory'].str.lower() == category.lower()]
        if filtered_df.empty:
            return JSONResponse(content={"message": f"No rows found for risk category '{category}'", "data": []})

        return JSONResponse(content={"data": filtered_df.to_dict(orient='records')})

    except Exception as e:
        logging.error(f"Failed to filter by risk category {category}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/risk_highest")
def get_highest_risks():
    return get_rows_by_risk_category("Highest Risk")

@router.get("/risk_high")
def get_high_risks():
    return get_rows_by_risk_category("High Risk")

@router.get("/risk_medium")
def get_medium_risks():
    return get_rows_by_risk_category("Medium Risk")

@router.get("/risk_low")
def get_low_risks():
    return get_rows_by_risk_category("Low Risk")

# --- Background task to scan files every 60 seconds ---
async def scan_files_for_warnings():
    while True:
        logging.info("Scanning Excel files for warnings...")
        warnings_list = []
        try:
            if not os.path.exists(MACHINES_BASE_PATH):
                logging.error(f"Machines base path does not exist: {MACHINES_BASE_PATH}")
                await asyncio.sleep(60)
                continue

            machine_dirs = [name for name in os.listdir(MACHINES_BASE_PATH)
                            if os.path.isdir(os.path.join(MACHINES_BASE_PATH, name))]

            for machine in machine_dirs:
                machine_path = os.path.join(MACHINES_BASE_PATH, machine, year, month, day)
                excel_file = os.path.join(machine_path, f"{machine}.xlsx")

                if not os.path.exists(excel_file):
                    logging.debug(f"No Excel file found for {machine}")
                    continue

                df = pd.read_excel(excel_file)

                required_columns = {'PlantID', 'ShopID', 'Machine', 'MachineID', 'Timestamp', 'Part', 'Value', 'Unit'}
                if not required_columns.issubset(df.columns):
                    logging.warning(f"Missing columns in {excel_file}")
                    continue

                cond = ((df['Unit'] == 'mm/sec') & (df['Value'] > 8)) | \
                       ((df['Unit'] == 'Degree C') & (df['Value'] > 70))
                warning_rows = df.loc[cond, ['PlantID', 'ShopID', 'Machine', 'MachineID', 'Timestamp', 'Part', 'Value', 'Unit']].copy()
                warning_rows['Status'] = 'Warning'

                # Risk Category for vibration levels
                warning_rows['RiskCategory'] = 'NA'
                mask = warning_rows['Unit'] == 'mm/sec'
                warning_rows.loc[mask, 'RiskCategory'] = np.where(warning_rows.loc[mask, 'Value'] < 8, 'No Risk',
                                                            np.where(
                                                                warning_rows.loc[mask, 'Value'] < 10, 'Low Risk',
                                                                np.where(
                                                                    warning_rows.loc[mask, 'Value'] < 13, 'Medium Risk',
                                                                    np.where(
                                                                        warning_rows.loc[mask, 'Value'] < 15, 'High Risk',
                                                                        'Highest Risk'
                                                                    )
                                                                )
                                                            )
                                                        )

                warnings_list.extend(warning_rows.to_dict(orient='records'))

                # Save/append warnings Excel file
                try:
                    warnings_df = warning_rows.copy()
                    if os.path.exists(warning_excel_path):
                        existing_df = pd.read_excel(warning_excel_path).copy()
                        combined_df = pd.concat([existing_df, warnings_df], ignore_index=True)
                        combined_df.drop_duplicates(subset=["Machine", "Timestamp", "Part"], inplace=True)
                    else:
                        combined_df = warnings_df

                    combined_df.to_excel(warning_excel_path, index=False, engine='openpyxl')
                    logging.info(f"Appended warnings to Excel: {warning_excel_path}")
                except Exception as e:
                    logging.error(f"Error writing warnings to Excel: {e}")

            logging.info(f"Warnings found: {len(warnings_list)}")
        except Exception as e:
            logging.error(f"Exception in warning scan: {e}")

        global warnings_cache
        warnings_cache = warnings_list
        await asyncio.sleep(60)

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(scan_files_for_warnings())
'''
