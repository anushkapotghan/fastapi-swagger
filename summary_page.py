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

# ✅ New: Use direct file path in root directory
warning_excel_path = f"warnings_{year}_{month}_{day}.xlsx"

@router.get("/machines")
def list_machines():
    global all_machines_df
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
    data =  non_operational_df.to_dict(orient="records")
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
            return JSONResponse(status_code=400, content={"error": f"Excel file must contain columns: {', '.join(required_columns)}"})
        unique_rows = df[list(required_columns)].drop_duplicates()
        return JSONResponse(content={"machines_with_warnings": unique_rows.to_dict(orient='records')})
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


async def scan_files_for_warnings():
    while True:
        logging.info("Scanning Excel files for warnings...")
        warnings_list = []
        try:
            # Skipped scanning MachinePulseData folder since it's not available
            # Instead, you can optionally handle file creation or log
            logging.info("MachinePulseData folder scan skipped (folder not found).")
        except Exception as e:
            logging.error(f"Exception in warning scan: {e}")

        global warnings_cache
        warnings_cache = warnings_list
        await asyncio.sleep(60)


@router.on_event("startup")
async def startup_event():
    asyncio.create_task(scan_files_for_warnings())
