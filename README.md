
# Urban Pulse — NYC 311 Service Request Analytics

An interactive data analytics dashboard built using Python, MySQL, Streamlit, and Plotly.

## Project Overview

Urban Pulse analyzes 100,000 NYC 311 service requests to understand complaint patterns, agency workloads, borough-level performance, and resolution times.

## Technologies Used

- Python
- Pandas and NumPy
- MySQL
- SQLAlchemy and PyMySQL
- Streamlit
- Plotly
- Matplotlib and Seaborn

## Project Features

- Interactive Borough, Agency, Complaint Type, and Status filters
- Date range filtering
- Key Performance Indicators (KPIs)
- Top 10 complaint types
- Borough-wise complaint analysis
- Agency workload analysis
- Daily complaint trends
- Complaint status distribution
- Resolution time distribution
- Median resolution time analysis
- IQR outlier detection
- Skewness analysis
- Insights and recommendations

## Key Findings

| Metric | Result |
|---|---|
| Total Service Requests | 100,000 |
| Closed Requests | 65,203 |
| Closure Rate | 65.20% |
| Median Resolution Time | 2.71 hours |
| Most Reported Complaint | Illegal Parking |
| Borough with Most Requests | Brooklyn |
| Agency with Most Requests | NYPD |

## Project Structure

```text
URBAN_PULSE/
├── app.py
├── scripts/
│   ├── 01_fetch_data.py
│   ├── 02_clean_data.py
│   ├── 03_eda_analysis.py
│   ├── 04_eda_charts.py
│   └── 05_load_mysql.py
├── charts/
├── data/
├── sql/
├── requirements.txt
├── .gitignore
└── README.md
```

The CSV datasets are excluded from GitHub.

## Installation

Clone the repository:

```bash
git clone https://github.com/muthupalpandiyan12-hub/Urban-Pulse-NYC-311-Analytics.git
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set up a local MySQL database named `urban_pulse` and populate the `nyc_311_full` table with the required NYC 311 data.

Run the dashboard:

```bash
streamlit run app.py
```

Enter your local MySQL password when prompted.

## Dataset

NYC 311 Service Request data covering November 6–15, 2026.

The project analyzes a 100,000-record extract. The final day may contain partial-day data.

## Conclusion

Urban Pulse demonstrates how Python, SQL, statistical analysis, and interactive visualizations can help identify urban service request patterns and operational improvement opportunities.

## Author

GitHub: [muthupalpandiyan12-hub](https://github.com/muthupalpandiyan12-hub)
