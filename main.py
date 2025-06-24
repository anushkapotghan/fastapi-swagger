# To run:
# python -m uvicorn yourfilename:app --reload

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import os
import pandas as pd
import asyncio
from datetime import datetime
import logging
import numpy as np
from fastapi import Path

from summary_page import router as summary_router
from tc1_asu1_door_side_routes import router as tc1_asu1_door_side_router
# from tc1_asu1_wall_side_routes import router as tc1_asu1_wall_side_router

app = FastAPI()

# Path to the folder that contains machine folders
# MACHINES_BASE_PATH = "./MachinePulseData"

# Plant, Shop, Machine details
all_machines_df = pd.read_excel("./MachinePulseData/MachinePulse_All_Machines.xlsx")

# # global parameters
# global today
# global year
# global month 
# global day
# global excel_path   # warning excel file path

# today = datetime.utcnow()
# year = str(today.year)
# month = str(today.month)
# day = str(today.day)
# excel_path = os.path.join(MACHINES_BASE_PATH, f"warnings_{year}_{month}_{str(today.day)}.xlsx") # warning excel file path

# Pass the DataFrame to the router by setting the global variable
import summary_page
summary_page.all_machines_df = all_machines_df
app.include_router(summary_router)

# # tc1_asu1_fan_1_door_side machine
# app.include_router(tc1_asu1_door_side_router)

# # tc1_asu1_fan_1_wall_side machine
# app.include_router(tc1_asu1_wall_side_router)
