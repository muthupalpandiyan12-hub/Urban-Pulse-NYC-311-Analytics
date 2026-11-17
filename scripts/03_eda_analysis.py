
import pandas as pd
import numpy as np
from pathlib import Path

# ======================================
# URBAN PULSE - MODULE 3
# STEP 1: STATISTICAL ANALYSIS
# ======================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "cleaned_data.csv"

df = pd.read_csv(DATA_FILE, low_memory=False)

print("=" * 55)
print("URBAN PULSE - STATISTICAL ANALYSIS")
print("=" * 55)

print(f"\nTotal Records: {len(df):,}")

# Resolution durations
resolution = pd.to_numeric(
    df["resolution_hours"],
    errors="coerce"
).dropna()

print("\n1. CENTRAL TENDENCY")
print(f"Mean: {resolution.mean():.2f} hours")
print(f"Median: {resolution.median():.2f} hours")

mode_values = resolution.mode()
if not mode_values.empty:
    print(f"Mode: {mode_values.iloc[0]:.2f} hours")

print("\n2. MEASURES OF SPREAD")
print(f"Minimum: {resolution.min():.2f}")
print(f"Maximum: {resolution.max():.2f}")
print(f"Range: {resolution.max() - resolution.min():.2f}")
print(f"Variance: {resolution.var():.2f}")
print(f"Standard Deviation: {resolution.std():.2f}")

# Quartiles and IQR
q1 = resolution.quantile(0.25)
q3 = resolution.quantile(0.75)
iqr = q3 - q1

lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

print("\n3. QUARTILES AND IQR")
print(f"Q1: {q1:.2f}")
print(f"Q3: {q3:.2f}")
print(f"IQR: {iqr:.2f}")
print(f"Lower Bound: {lower_bound:.2f}")
print(f"Upper Bound: {upper_bound:.2f}")

# Detect outliers
outliers = resolution[
    (resolution < lower_bound) |
    (resolution > upper_bound)
]

print("\n4. OUTLIER ANALYSIS")
print(f"Total Outliers: {len(outliers):,}")
print(f"Outlier Percentage: {len(outliers) / len(resolution) * 100:.2f}%")

print("\n5. SKEWNESS")
print(f"Skewness: {resolution.skew():.2f}")

print("\n6. TOP 10 COMPLAINT TYPES")
print(df["complaint_type"].value_counts().head(10))

print("\n7. BOROUGH DISTRIBUTION")
print(df["borough"].value_counts())

print("\n8. AGENCY WORKLOAD")
print(df["agency"].value_counts().head(10))

print("\nSTATISTICAL ANALYSIS COMPLETED")
