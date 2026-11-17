
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# URBAN PULSE - EDA VISUALIZATIONS

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "cleaned_data.csv"
CHART_DIR = BASE_DIR / "charts"

CHART_DIR.mkdir(exist_ok=True)

df = pd.read_csv(DATA_FILE, low_memory=False)

sns.set_theme(style="whitegrid")

print("URBAN PULSE - CREATING EDA CHARTS")

# 1. Top 10 complaint categories
plt.figure(figsize=(12, 6))
top_complaints = df["complaint_type"].value_counts().head(10)

sns.barplot(
    x=top_complaints.values,
    y=top_complaints.index,
    color="steelblue"
)

plt.title("Top 10 NYC Complaint Categories")
plt.xlabel("Number of Complaints")
plt.ylabel("Complaint Type")
plt.tight_layout()
plt.savefig(CHART_DIR / "01_top_complaints.png", dpi=150)
plt.close()

print("Chart 1 created")

# 2. Borough distribution
plt.figure(figsize=(10, 5))
borough_counts = df["borough"].value_counts()

sns.barplot(
    x=borough_counts.index,
    y=borough_counts.values,
    color="teal"
)

plt.title("Complaint Distribution by Borough")
plt.xlabel("Borough")
plt.ylabel("Number of Complaints")
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(CHART_DIR / "02_borough_distribution.png", dpi=150)
plt.close()

print("Chart 2 created")

# 3. Agency workload
plt.figure(figsize=(10, 6))
agency_counts = df["agency"].value_counts().head(10)

sns.barplot(
    x=agency_counts.values,
    y=agency_counts.index,
    color="coral"
)

plt.title("Top 10 Agencies by Complaint Volume")
plt.xlabel("Number of Complaints")
plt.ylabel("Agency")
plt.tight_layout()
plt.savefig(CHART_DIR / "03_agency_workload.png", dpi=150)
plt.close()

print("Chart 3 created")

# 4. Resolution time histogram
resolution = pd.to_numeric(
    df["resolution_hours"], errors="coerce"
).dropna()

plt.figure(figsize=(10, 6))
sns.histplot(resolution, bins=50, color="purple")

plt.title("Distribution of Resolution Time")
plt.xlabel("Resolution Time (Hours)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(CHART_DIR / "04_resolution_histogram.png", dpi=150)
plt.close()

print("Chart 4 created")

# 5. Resolution time boxplot
plt.figure(figsize=(10, 4))
sns.boxplot(x=resolution, color="orange")

plt.title("Resolution Time Outlier Analysis")
plt.xlabel("Resolution Time (Hours)")
plt.tight_layout()
plt.savefig(CHART_DIR / "05_resolution_boxplot.png", dpi=150)
plt.close()

print("Chart 5 created")

# 6. Monthly complaint trend
df["created_date"] = pd.to_datetime(
    df["created_date"], errors="coerce"
)

monthly = (
    df.dropna(subset=["created_date"])
    .set_index("created_date")
    .resample("MS")
    .size()
)

plt.figure(figsize=(12, 5))
plt.plot(monthly.index, monthly.values, marker="o")

plt.title("Monthly NYC Complaint Trend")
plt.xlabel("Month")
plt.ylabel("Number of Complaints")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(CHART_DIR / "06_monthly_trend.png", dpi=150)
plt.close()

print("Chart 6 created")

print("\nSUCCESS: All 6 EDA charts saved!")
print("Location:", CHART_DIR)
