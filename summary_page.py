import pandas as pd

# Correct path since file is in root directory
file_path = "warnings_2025_6_19.xlsx"

try:
    df = pd.read_excel(file_path)
    print("File loaded successfully")
    # Continue with processing the dataframe
except FileNotFoundError:
    print(f"File not found: {file_path}")
except Exception as e:
    print(f"An error occurred: {e}")
