@app.get("/")
def read_root():
  return{"message": "FastAPI is live!"}
# # To run:
# # python -m uvicorn main:app --reload

# from fastapi import FastAPI, Query
# from fastapi.responses import JSONResponse
# import os
# import pandas as pd
# import asyncio
# from datetime import datetime
# import logging
# import numpy as np
# from fastapi import Path

# from summary_page import router as summary_router
# # Comment out these lines since the modules don't exist
# # from tc1_asu1_door_side_routes import router as tc1_asu1_door_side_router
# # from tc1_asu1_wall_side_routes import router as tc1_asu1_wall_side_router

# app = FastAPI()

# # Plant, Shop, Machine details
# # Comment out the path to the file since it doesn't exist
# # all_machines_df = pd.read_excel("C:/path/to/your/MachinePulse_All_Machines.xlsx")

# # Option 2: Create a dummy DataFrame for testing - UNCOMMENT THIS
# all_machines_df = pd.DataFrame({
#     'Machine': ['Machine1', 'Machine2', 'Machine3'],
#     'MachineStatus': ['Operational', 'Operational', 'Non_Operational'],
#     'MachineID': ['M001', 'M002', 'M003'],
#     'PlantID': ['Plant1', 'Plant2', 'Plant1'],
#     'ShopID': ['Shop1', 'Shop2', 'Shop1'],
#     'Location': ['Area1', 'Area2', 'Area3']
# })

# # Pass the DataFrame to the router by setting the global variable
# import summary_page
# summary_page.all_machines_df = all_machines_df
# app.include_router(summary_router)

# # Comment out any routers that don't have their modules available
# # app.include_router(tc1_asu1_door_side_router)




from fastapi import FastAPI
import pandas as pd

from summary_page import router as summary_router
from router import router as custom_router  # ✅ From router.py

app = FastAPI()

# Load machine data
all_machines_df = pd.read_excel("MachinePulse_All_Machines.xlsx")

# Pass it to summary_page module if needed
import summary_page
summary_page.all_machines_df = all_machines_df

# Include routers
app.include_router(summary_router)
app.include_router(custom_router)
