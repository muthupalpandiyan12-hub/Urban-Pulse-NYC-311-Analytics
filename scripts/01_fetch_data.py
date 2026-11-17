
import requests
import pandas as pd
import time
import json
from pathlib import Path
from datetime import datetime, timezone

# =====================================
# URBAN PULSE - MODULE 1
# NYC 311 DATA COLLECTION
# Target: 100,000 Records
# =====================================

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

TOTAL_RECORDS = 100000
BATCH_SIZE = 1000

# Project folder paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "raw_data.csv"
METADATA_FILE = DATA_DIR / "extraction_metadata.json"

# Fixed cutoff for reproducibility
extraction_time = datetime.now(timezone.utc)
cutoff = extraction_time.strftime("%Y-%m-%dT%H:%M:%S")

all_records = []
seen_ids = set()

session = requests.Session()

print("=" * 50)
print("URBAN PULSE - NYC 311 DATA COLLECTION")
print("=" * 50)
print(f"Target Records : {TOTAL_RECORDS:,}")
print(f"Batch Size     : {BATCH_SIZE:,}")
print(f"Extraction UTC : {cutoff}")
print("=" * 50)

try:
    for offset in range(0, TOTAL_RECORDS, BATCH_SIZE):

        params = {
            "$where": f"created_date < '{cutoff}'",
            "$limit": BATCH_SIZE,
            "$offset": offset,
            "$order": "created_date DESC, unique_key DESC"
        }

        records = None

        # Retry failed API requests
        for attempt in range(1, 4):
            try:
                response = session.get(
                    API_URL,
                    params=params,
                    timeout=90
                )

                response.raise_for_status()
                records = response.json()

                if not isinstance(records, list):
                    raise ValueError(
                        "Unexpected API response format"
                    )

                break

            except (
                requests.RequestException,
                ValueError
            ) as error:

                print(
                    f"Attempt {attempt} failed: {error}"
                )

                if attempt == 3:
                    raise

                time.sleep(attempt * 3)

        if not records:
            print("No more records available.")
            break

        # Avoid duplicate complaint IDs
        for record in records:

            request_id = record.get("unique_key")

            if request_id is None:
                continue

            if request_id not in seen_ids:
                seen_ids.add(request_id)
                all_records.append(record)

        print(
            f"Downloaded: {len(all_records):,} "
            f"unique records"
        )

        if len(records) < BATCH_SIZE:
            break

        time.sleep(0.3)

finally:
    session.close()

# =====================================
# SAVE RAW DATA
# =====================================

if not all_records:
    raise RuntimeError(
        "No records downloaded. Check API connection."
    )

df = pd.DataFrame(all_records)

# Save original API values without cleaning
df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

# Save extraction information
metadata = {
    "project": "URBAN PULSE",
    "source": API_URL,
    "extraction_utc": cutoff,
    "target_records": TOTAL_RECORDS,
    "actual_records": len(df),
    "total_columns": len(df.columns),
    "unique_request_ids": df["unique_key"].nunique(),
    "sampling_method": "Latest records by created_date",
    "output_file": str(OUTPUT_FILE)
}

with open(
    METADATA_FILE,
    "w",
    encoding="utf-8"
) as file:
    json.dump(metadata, file, indent=4)

# =====================================
# FINAL VALIDATION
# =====================================

print("\n" + "=" * 50)
print("DATA COLLECTION COMPLETED")
print("=" * 50)

print(f"Total Rows       : {len(df):,}")
print(f"Total Columns    : {len(df.columns)}")
print(
    f"Unique IDs       : "
    f"{df['unique_key'].nunique():,}"
)

print(f"CSV File         : {OUTPUT_FILE}")
print(f"Metadata File    : {METADATA_FILE}")

print("\nFirst 5 Records:")
print(df.head().to_string())

if len(df) == TOTAL_RECORDS:
    print("\nSUCCESS: 1,00,000 records collected!")
else:
    print(
        "\nWARNING: Target not fully reached."
    )
    print(
        "Check API availability and duplicate counts."
    )

print("=" * 50)
