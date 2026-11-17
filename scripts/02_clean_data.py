
import pandas as pd
from pathlib import Path

# ========================================
# URBAN PULSE - MODULE 2
# DATA CLEANING AND FEATURE ENGINEERING
# ========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RAW_FILE = DATA_DIR / "raw_data.csv"
CLEAN_FILE = DATA_DIR / "cleaned_data.csv"
QUALITY_FILE = DATA_DIR / "data_quality_report.csv"

print("=" * 55)
print("URBAN PULSE - DATA CLEANING")
print("=" * 55)

# 1. Load raw data
df = pd.read_csv(
    RAW_FILE,
    low_memory=False,
    dtype={
        "unique_key": "string",
        "incident_zip": "string",
        "bbl": "string"
    }
)

original_rows = len(df)
print(f"\nOriginal Records: {original_rows:,}")

# 2. Remove duplicate request IDs
duplicates = df["unique_key"].duplicated().sum()
df = df.drop_duplicates(
    subset=["unique_key"],
    keep="first"
).copy()

print(f"Duplicate IDs Removed: {duplicates}")

# 3. Clean important text columns
text_columns = [
    "agency",
    "agency_name",
    "complaint_type",
    "borough",
    "status",
    "descriptor",
    "city",
    "location_type"
]

for col in text_columns:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

# Standardize borough names
df["borough"] = df["borough"].str.upper()

# Standardize status
df["status"] = df["status"].str.title()

# 4. Convert date columns
date_columns = [
    "created_date",
    "closed_date",
    "due_date",
    "resolution_action_updated_date"
]

for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )

# 5. Convert geographic coordinates
for col in ["latitude", "longitude"]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# Flag invalid coordinates
df["valid_coordinates"] = (
    df["latitude"].between(-90, 90)
    & df["longitude"].between(-180, 180)
)

# 6. Calculate resolution duration
df["resolution_hours"] = (
    df["closed_date"] - df["created_date"]
).dt.total_seconds() / 3600

# Flag invalid negative durations
df["invalid_resolution"] = (
    df["resolution_hours"] < 0
)

df.loc[
    df["invalid_resolution"],
    "resolution_hours"
] = float("nan")

# 7. Create closure indicator
df["is_closed"] = df["closed_date"].notna()

# 8. Create date-related features
df["created_year"] = df["created_date"].dt.year
df["created_month"] = df["created_date"].dt.month
df["created_month_name"] = (
    df["created_date"].dt.month_name()
)
df["created_weekday"] = (
    df["created_date"].dt.day_name()
)
df["created_hour"] = df["created_date"].dt.hour

# 9. Save data quality report
quality_report = pd.DataFrame({
    "column": df.columns,
    "missing_count": df.isna().sum().values,
    "missing_percentage": (
        df.isna().mean().values * 100
    ).round(2)
})

quality_report.to_csv(
    QUALITY_FILE,
    index=False
)

# 10. Save cleaned dataset
df.to_csv(
    CLEAN_FILE,
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d %H:%M:%S"
)

# 11. Display results
print("\n" + "=" * 55)
print("DATA CLEANING COMPLETED")
print("=" * 55)

print(f"Original Rows       : {original_rows:,}")
print(f"Cleaned Rows        : {len(df):,}")
print(f"Total Columns       : {len(df.columns)}")
print(f"Duplicate IDs       : {df['unique_key'].duplicated().sum()}")
print(f"Closed Requests     : {df['is_closed'].sum():,}")
print(f"Open/Unclosed       : {(~df['is_closed']).sum():,}")
print(f"Invalid Durations   : {df['invalid_resolution'].sum():,}")
print(f"Valid Coordinates   : {df['valid_coordinates'].sum():,}")

print("\nResolution Statistics (Hours)")
print(df["resolution_hours"].describe())

print("\nFiles Created:")
print(CLEAN_FILE)
print(QUALITY_FILE)

print("\nSUCCESS: Module 2 Data Cleaning Finished!")
