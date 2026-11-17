import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os
from datetime import timedelta

st.set_page_config(page_title="Urban Pulse Dashboard", page_icon="🏙️", layout="wide")
st.title("🏙️ Urban Pulse")
st.header("NYC 311 Service Request Analytics")
st.write("Live analytics from the Urban Pulse MySQL database.")

password = st.text_input("MySQL password", type="password")
load_dashboard = st.button("Load Dashboard", type="primary")

if load_dashboard:
    st.session_state["dashboard_loaded"] = True

if st.session_state.get("dashboard_loaded", False):
    if not password:
        st.warning("Please enter your MySQL password.")
        st.stop()

    engine = None
    try:
        # Keep the password out of source code and Git history.
        # Non-secret connection settings can be supplied via environment variables.
        database_url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv("MYSQL_USER", "root"),
            password=password,
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "urban_pulse"),
        )
        engine = create_engine(database_url, pool_pre_ping=True)

        # Filters are built from the original table, before loading dashboard data.
        # A temporary table keeps every existing analytical query unchanged in structure.
        with engine.connect() as connection:
            st.subheader("Interactive Filters")
            st.caption("Change a filter to refresh all dashboard sections automatically.")

            borough_options = pd.read_sql(text("""
                SELECT DISTINCT COALESCE(NULLIF(TRIM(borough), ''), 'UNSPECIFIED') AS item
                FROM nyc_311_full ORDER BY item
            """), connection)["item"].tolist()
            agency_options = pd.read_sql(text("""
                SELECT DISTINCT agency AS item FROM nyc_311_full
                WHERE agency IS NOT NULL AND TRIM(agency) <> '' ORDER BY item
            """), connection)["item"].tolist()
            complaint_options = pd.read_sql(text("""
                SELECT DISTINCT complaint_type AS item FROM nyc_311_full
                WHERE complaint_type IS NOT NULL AND TRIM(complaint_type) <> '' ORDER BY item
            """), connection)["item"].tolist()
            status_options = pd.read_sql(text("""
                SELECT DISTINCT COALESCE(NULLIF(TRIM(status), ''), 'Unspecified') AS item
                FROM nyc_311_full ORDER BY item
            """), connection)["item"].tolist()
            date_bounds = pd.read_sql(text("""
                SELECT MIN(DATE(STR_TO_DATE(created_date, '%Y-%m-%d %H:%i:%s'))) AS min_date,
                       MAX(DATE(STR_TO_DATE(created_date, '%Y-%m-%d %H:%i:%s'))) AS max_date
                FROM nyc_311_full
            """), connection)
            min_date = pd.to_datetime(date_bounds.iloc[0]["min_date"]).date()
            max_date = pd.to_datetime(date_bounds.iloc[0]["max_date"]).date()

            f1, f2, f3, f4 = st.columns(4)
            with f1:
                selected_borough = st.selectbox("Borough", ["All"] + borough_options)
            with f2:
                selected_agency = st.selectbox("Agency", ["All"] + agency_options)
            with f3:
                selected_complaint = st.selectbox("Complaint Type", ["All"] + complaint_options)
            with f4:
                selected_status = st.selectbox("Status", ["All"] + status_options)

            d1, d2 = st.columns(2)
            with d1:
                start_date = st.date_input("From Date", value=min_date,
                                           min_value=min_date, max_value=max_date)
            with d2:
                end_date = st.date_input("To Date", value=max_date,
                                         min_value=min_date, max_value=max_date)
            if start_date > end_date:
                st.warning("From Date must not be later than To Date.")
                st.stop()

            conditions = [
                "created_date >= :start_datetime",
                "created_date < :end_datetime",
            ]
            params = {
                "start_datetime": start_date.strftime("%Y-%m-%d 00:00:00"),
                "end_datetime": (end_date + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
            }
            if selected_borough != "All":
                conditions.append("COALESCE(NULLIF(TRIM(borough), ''), 'UNSPECIFIED') = :borough")
                params["borough"] = selected_borough
            if selected_agency != "All":
                conditions.append("agency = :agency")
                params["agency"] = selected_agency
            if selected_complaint != "All":
                conditions.append("complaint_type = :complaint")
                params["complaint"] = selected_complaint
            if selected_status != "All":
                conditions.append("COALESCE(NULLIF(TRIM(status), ''), 'Unspecified') = :status")
                params["status"] = selected_status

            connection.execute(text("DROP TEMPORARY TABLE IF EXISTS filtered_311"))
            connection.execute(text(
                "CREATE TEMPORARY TABLE filtered_311 AS "
                "SELECT * FROM nyc_311_full WHERE " + " AND ".join(conditions)
            ), params)
            filtered_count = connection.execute(
                text("SELECT COUNT(*) FROM filtered_311")
            ).scalar_one()
            if filtered_count == 0:
                st.warning("No records match these filters. Adjust your selections.")
                st.stop()
            st.caption(f"Showing {filtered_count:,} matching service requests.")

            # Load filtered data while the connection is open; render charts afterward.
            summary_df = pd.read_sql(text("""
                SELECT COUNT(*) AS total_requests,
                       SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed_requests
                FROM filtered_311
            """), connection)

            # Use the existing cleaned numeric column for consistent resolution analysis.
            resolution_df = pd.read_sql(text("""
                SELECT resolution_hours
                FROM filtered_311
                WHERE status = 'Closed'
                  AND resolution_hours IS NOT NULL
                  AND resolution_hours >= 0
            """), connection)

            complaint_df = pd.read_sql(text("""
                SELECT complaint_type, COUNT(*) AS total_requests
                FROM filtered_311
                WHERE complaint_type IS NOT NULL AND TRIM(complaint_type) <> ''
                GROUP BY complaint_type
                ORDER BY total_requests DESC
                LIMIT 10
            """), connection)

            borough_df = pd.read_sql(text("""
                SELECT COALESCE(NULLIF(TRIM(borough), ''), 'UNSPECIFIED') AS borough,
                       COUNT(*) AS total_requests,
                       SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed_requests
                FROM filtered_311
                GROUP BY COALESCE(NULLIF(TRIM(borough), ''), 'UNSPECIFIED')
                ORDER BY total_requests DESC
            """), connection)

            agency_df = pd.read_sql(text("""
                SELECT agency, COUNT(*) AS total_requests,
                       SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed_requests,
                       ROUND(100.0 * SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END)
                             / COUNT(*), 2) AS closure_rate
                FROM filtered_311
                WHERE agency IS NOT NULL AND TRIM(agency) <> ''
                GROUP BY agency
                ORDER BY total_requests DESC
            """), connection)

            daily_df = pd.read_sql(text("""
                SELECT DATE(STR_TO_DATE(created_date, '%Y-%m-%d %H:%i:%s')) AS complaint_date,
                       COUNT(*) AS total_requests
                FROM filtered_311
                WHERE created_date IS NOT NULL
                  AND STR_TO_DATE(created_date, '%Y-%m-%d %H:%i:%s') IS NOT NULL
                GROUP BY complaint_date
                ORDER BY complaint_date
            """), connection)

            status_df = pd.read_sql(text("""
                SELECT COALESCE(NULLIF(TRIM(status), ''), 'Unspecified') AS complaint_status,
                       COUNT(*) AS total_requests,
                       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)
                           AS percentage
                FROM filtered_311
                GROUP BY complaint_status
                ORDER BY total_requests DESC
            """), connection)

            # STEP 8: Median resolution time by complaint category.
            # MySQL 8+ window functions; median handles odd/even group sizes.
            category_median_df = pd.read_sql(text("""
                WITH ranked AS (
                    SELECT
                        complaint_type,
                        resolution_hours,
                        ROW_NUMBER() OVER (
                            PARTITION BY complaint_type
                            ORDER BY resolution_hours
                        ) AS rn,
                        COUNT(*) OVER (
                            PARTITION BY complaint_type
                        ) AS total_closed
                    FROM filtered_311
                    WHERE status = 'Closed'
                      AND complaint_type IS NOT NULL
                      AND TRIM(complaint_type) <> ''
                      AND resolution_hours IS NOT NULL
                      AND resolution_hours >= 0
                ),
                category_stats AS (
                    SELECT
                        complaint_type,
                        MAX(total_closed) AS valid_closed_requests,
                        ROUND(AVG(resolution_hours), 2) AS median_resolution_hours
                    FROM ranked
                    WHERE rn IN (
                        FLOOR((total_closed + 1) / 2),
                        FLOOR((total_closed + 2) / 2)
                    )
                    GROUP BY complaint_type
                )
                SELECT
                    complaint_type,
                    valid_closed_requests,
                    median_resolution_hours
                FROM category_stats
                WHERE valid_closed_requests >= 30
                ORDER BY median_resolution_hours DESC
                LIMIT 10
            """), connection)

            # STEP 9: Median resolution time by agency (MySQL 8+).
            agency_median_df = pd.read_sql(text("""
                WITH ranked AS (
                    SELECT
                        agency,
                        resolution_hours,
                        ROW_NUMBER() OVER (
                            PARTITION BY agency
                            ORDER BY resolution_hours
                        ) AS rn,
                        COUNT(*) OVER (
                            PARTITION BY agency
                        ) AS total_requests
                    FROM filtered_311
                    WHERE status = 'Closed'
                      AND resolution_hours IS NOT NULL
                      AND resolution_hours >= 0
                      AND agency IS NOT NULL
                      AND TRIM(agency) <> ''
                ),
                agency_stats AS (
                    SELECT
                        agency,
                        MAX(total_requests) AS valid_closed_requests,
                        ROUND(AVG(CASE
                            WHEN rn IN (
                                FLOOR((total_requests + 1) / 2),
                                FLOOR((total_requests + 2) / 2)
                            ) THEN resolution_hours
                        END), 2) AS median_resolution_hours
                    FROM ranked
                    GROUP BY agency
                )
                SELECT
                    agency,
                    valid_closed_requests,
                    median_resolution_hours
                FROM agency_stats
                WHERE valid_closed_requests >= 30
                ORDER BY median_resolution_hours DESC
            """), connection)

        total_requests = int(summary_df["total_requests"].iloc[0])
        closed_requests = int(summary_df["closed_requests"].fillna(0).iloc[0])
        closure_rate = 100 * closed_requests / total_requests if total_requests else 0
        resolution_df["resolution_hours"] = pd.to_numeric(
            resolution_df["resolution_hours"], errors="coerce"
        )
        resolution_df = resolution_df.dropna(subset=["resolution_hours"])
        median_resolution = (resolution_df["resolution_hours"].median()
                             if not resolution_df.empty else 0)
        average_resolution = (resolution_df["resolution_hours"].mean()
                              if not resolution_df.empty else 0)
        resolved_after_72 = (100 * resolution_df["resolution_hours"].gt(72).mean()
                             if not resolution_df.empty else 0)
        borough_df["closure_rate"] = (
            100 * borough_df["closed_requests"] / borough_df["total_requests"]
        ).round(2)

        st.success("Dashboard data loaded successfully!")

        # STEP 1: KPIs
        st.header("Key Performance Indicators")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Requests", f"{total_requests:,}")
        c2.metric("Closed Requests", f"{closed_requests:,}")
        c3.metric("Closure Rate", f"{closure_rate:.2f}%")
        c4.metric("Median Resolution", f"{median_resolution:.2f} hrs")
        c5.metric("Resolved After 72h", f"{resolved_after_72:.2f}%")
        st.caption(f"Requests not marked Closed: {total_requests - closed_requests:,}. "
                   "Resolution metrics use valid closed requests only.")

        # STEP 2: Top complaint types
        st.divider()
        st.header("Top 10 Complaint Types")
        complaint_fig = px.bar(
            complaint_df, x="total_requests", y="complaint_type", orientation="h",
            color="total_requests", text="total_requests", color_continuous_scale="Blues"
        )
        complaint_fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Number of Requests", yaxis_title="Complaint Type",
            coloraxis_showscale=False, height=550
        )
        complaint_fig.update_traces(textposition="outside")
        st.plotly_chart(complaint_fig, use_container_width=True)
        st.subheader("Complaint Summary")
        st.dataframe(complaint_df, use_container_width=True, hide_index=True)

        # STEP 3: Borough analysis
        st.divider()
        st.header("Borough-wise Complaint Analysis")
        st.write("Comparison of NYC 311 service requests across different boroughs.")
        borough_fig = px.bar(
            borough_df, x="borough", y="total_requests", color="borough",
            text="total_requests", title="Total Complaints by Borough"
        )
        borough_fig.update_layout(
            xaxis_title="Borough", yaxis_title="Number of Complaints",
            showlegend=False, height=500
        )
        borough_fig.update_traces(textposition="outside")
        st.plotly_chart(borough_fig, use_container_width=True)
        st.subheader("Borough Complaint Summary")
        st.dataframe(borough_df, use_container_width=True, hide_index=True)
        st.header("Key Insights")
        if not borough_df.empty:
            top_borough = borough_df.iloc[0]
            st.info(f"{top_borough['borough']} recorded the highest number of complaints "
                    f"({int(top_borough['total_requests']):,}).")
        st.info(f"The overall complaint closure rate is {closure_rate:.2f}%.")

        # STEP 4: Agency performance
        st.divider()
        st.header("Step 4 - Agency Performance Analysis")
        st.subheader("Complaints by Agency")
        agency_fig = px.bar(
            agency_df, x="agency", y="total_requests", color="closure_rate",
            text="total_requests", title="Total Complaints by Agency",
            labels={"agency": "Agency", "total_requests": "Total Requests",
                    "closure_rate": "Closure Rate (%)"}
        )
        agency_fig.update_traces(textposition="outside")
        st.plotly_chart(agency_fig, use_container_width=True)
        st.subheader("Agency Closure Rate")
        agency_rate_fig = px.bar(
            agency_df, x="agency", y="closure_rate", text="closure_rate",
            title="Agency-wise Closure Percentage",
            labels={"agency": "Agency", "closure_rate": "Closure Rate (%)"}
        )
        agency_rate_fig.update_traces(textposition="outside")
        st.plotly_chart(agency_rate_fig, use_container_width=True)
        st.subheader("Agency Performance Summary")
        st.dataframe(agency_df, use_container_width=True, hide_index=True)

        # STEP 5: Daily trend
        st.divider()
        st.header("Step 5 - Daily Complaint Trend Analysis")
        daily_df["complaint_date"] = pd.to_datetime(daily_df["complaint_date"])
        st.subheader("Daily NYC 311 Complaints")
        daily_fig = px.line(
            daily_df, x="complaint_date", y="total_requests", markers=True,
            title="Daily Complaint Trend",
            labels={"complaint_date": "Date", "total_requests": "Number of Complaints"}
        )
        st.plotly_chart(daily_fig, use_container_width=True)
        st.subheader("Daily Complaint Summary")
        st.dataframe(daily_df, use_container_width=True, hide_index=True)
        if not daily_df.empty:
            peak_day = daily_df.loc[daily_df["total_requests"].idxmax()]
            st.info(f"Highest complaints recorded on "
                    f"{peak_day['complaint_date']:%d-%m-%Y}: "
                    f"{int(peak_day['total_requests']):,} requests.")
        st.caption("The date range is short; the final day may be incomplete.")

        # STEP 6: Status analysis
        st.divider()
        st.header("Step 6 - Complaint Status Analysis")
        st.subheader("Complaints by Status")
        status_fig = px.pie(
            status_df, names="complaint_status", values="total_requests",
            hole=0.45, title="NYC 311 Complaint Status Distribution"
        )
        status_fig.update_traces(textinfo="percent+label")
        st.plotly_chart(status_fig, use_container_width=True)
        st.subheader("Complaint Status Summary")
        st.dataframe(status_df, use_container_width=True, hide_index=True)
        status_closed = int(status_df.loc[
            status_df["complaint_status"] == "Closed", "total_requests"
        ].sum())
        status_total = int(status_df["total_requests"].sum())
        s1, s2, s3 = st.columns(3)
        s1.metric("Total Complaints", f"{status_total:,}")
        s2.metric("Closed Complaints", f"{status_closed:,}")
        s3.metric("Not Marked Closed", f"{status_total - status_closed:,}")
        st.info(f"{100 * status_closed / status_total:.2f}% of complaints are marked Closed."
                if status_total else "No complaint status data available.")

        # STEP 7: Resolution time analysis
        st.divider()
        st.header("Step 7 - Resolution Time Analysis")
        st.write("Resolution times for closed requests with valid non-negative durations.")
        if resolution_df.empty:
            st.warning("No valid resolution time records were found.")
        else:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Valid Closed Requests", f"{len(resolution_df):,}")
            r2.metric("Average Resolution", f"{average_resolution:.2f} hrs")
            r3.metric("Median Resolution", f"{median_resolution:.2f} hrs")
            r4.metric("Resolved After 72h", f"{resolved_after_72:.2f}%")

            # Mutually exclusive ranges: [0,1), [1,6), ... [72,infinity).
            bins = [0, 1, 6, 12, 24, 48, 72, float("inf")]
            labels = ["Under 1 hour", "1-6 hours", "6-12 hours", "12-24 hours",
                      "24-48 hours", "48-72 hours", "Over 72 hours"]
            durations = pd.cut(
                resolution_df["resolution_hours"], bins=bins, labels=labels,
                right=False, include_lowest=True
            )
            range_counts = durations.value_counts(sort=False)
            resolution_summary = pd.DataFrame({
                "resolution_range": labels,
                "total_requests": [int(range_counts.get(label, 0)) for label in labels],
            })
            resolution_summary["percentage"] = (
                100 * resolution_summary["total_requests"] / len(resolution_df)
            ).round(2)

            st.subheader("Closed Requests by Resolution Time")
            resolution_fig = px.bar(
                resolution_summary, x="resolution_range", y="total_requests",
                text="total_requests", color="total_requests",
                color_continuous_scale="Blues",
                title="Resolution Time Distribution",
                labels={"resolution_range": "Resolution Time",
                        "total_requests": "Closed Requests"}
            )
            resolution_fig.update_layout(coloraxis_showscale=False, height=480)
            resolution_fig.update_traces(textposition="outside")
            st.plotly_chart(resolution_fig, use_container_width=True)
            st.subheader("Resolution Time Summary")
            st.dataframe(resolution_summary, use_container_width=True, hide_index=True)
            st.info(f"{100 * resolution_df['resolution_hours'].lt(6).mean():.2f}% of "
                    "valid closed requests were resolved in under 6 hours.")

        # STEP 8: Median resolution time by complaint category
        st.divider()
        st.header("Step 8 - Median Resolution Time by Complaint Category")
        st.write(
            "Top 10 complaint categories with the longest median resolution times "
            "among closed requests with valid non-negative durations."
        )
        st.caption("Categories require at least 30 valid closed requests.")
        if category_median_df.empty:
            st.warning("No complaint categories met the minimum record threshold.")
        else:
            category_median_df["median_resolution_hours"] = pd.to_numeric(
                category_median_df["median_resolution_hours"], errors="coerce"
            )
            category_median_df["valid_closed_requests"] = pd.to_numeric(
                category_median_df["valid_closed_requests"], errors="coerce"
            )
            category_median_df = category_median_df.dropna(
                subset=["median_resolution_hours", "valid_closed_requests"]
            )
            if category_median_df.empty:
                st.warning("No valid category median results are available.")
            else:
                st.subheader("Top 10 Slowest Complaint Categories")
                category_fig = px.bar(
                    category_median_df,
                    x="median_resolution_hours",
                    y="complaint_type",
                    orientation="h",
                    color="median_resolution_hours",
                    color_continuous_scale="Blues",
                    text="median_resolution_hours",
                    hover_data=["valid_closed_requests"],
                    title="Median Resolution Time by Complaint Category",
                    labels={
                        "complaint_type": "Complaint Type",
                        "median_resolution_hours": "Median Resolution (hours)",
                        "valid_closed_requests": "Valid Closed Requests",
                    },
                )
                category_fig.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    coloraxis_showscale=False,
                    height=550,
                )
                category_fig.update_traces(textposition="outside")
                st.plotly_chart(category_fig, use_container_width=True)

                st.subheader("Category Median Resolution Summary")
                st.dataframe(category_median_df, use_container_width=True, hide_index=True)
                slowest = category_median_df.iloc[0]
                st.info(
                    f"{slowest['complaint_type']} has the longest median resolution "
                    f"time at {slowest['median_resolution_hours']:.2f} hours "
                    f"across {int(slowest['valid_closed_requests']):,} valid closed requests."
                )

        # STEP 9: Median resolution time by agency
        st.divider()
        st.header("Step 9 - Median Resolution Time by Agency")
        st.write(
            "Compare typical resolution times across NYC agencies using closed "
            "requests with valid non-negative durations."
        )
        st.caption("Agencies require at least 30 valid closed requests.")

        if agency_median_df.empty:
            st.warning("No agencies met the minimum record threshold.")
        else:
            agency_median_df["median_resolution_hours"] = pd.to_numeric(
                agency_median_df["median_resolution_hours"], errors="coerce"
            )
            agency_median_df["valid_closed_requests"] = pd.to_numeric(
                agency_median_df["valid_closed_requests"], errors="coerce"
            )
            agency_median_df = agency_median_df.dropna(
                subset=["median_resolution_hours", "valid_closed_requests"]
            )

            if agency_median_df.empty:
                st.warning("No valid agency median results are available.")
            else:
                st.subheader("Agency Median Resolution Comparison")
                agency_median_fig = px.bar(
                    agency_median_df,
                    x="median_resolution_hours",
                    y="agency",
                    orientation="h",
                    color="median_resolution_hours",
                    color_continuous_scale="Blues",
                    text="median_resolution_hours",
                    hover_data=["valid_closed_requests"],
                    title="Median Resolution Time by Agency",
                    labels={
                        "agency": "Agency",
                        "median_resolution_hours": "Median Resolution (hours)",
                        "valid_closed_requests": "Valid Closed Requests",
                    },
                )
                agency_median_fig.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    coloraxis_showscale=False,
                    height=550,
                )
                agency_median_fig.update_traces(textposition="outside")
                st.plotly_chart(agency_median_fig, use_container_width=True)

                st.subheader("Agency Median Resolution Summary")
                st.dataframe(
                    agency_median_df, use_container_width=True, hide_index=True
                )
                slowest_agency = agency_median_df.iloc[0]
                fastest_agency = agency_median_df.iloc[-1]
                st.info(
                    f"{slowest_agency['agency']} has the longest median resolution "
                    f"time at {slowest_agency['median_resolution_hours']:.2f} hours "
                    f"across {int(slowest_agency['valid_closed_requests']):,} "
                    "valid closed requests."
                )
                st.info(
                    f"{fastest_agency['agency']} has the shortest median resolution "
                    f"time among qualifying agencies at "
                    f"{fastest_agency['median_resolution_hours']:.2f} hours."
                )
                st.caption(
                    "Agency comparisons reflect different types of complaints and "
                    "should not be interpreted as a direct performance ranking."
                )

        # STEP 10: IQR outlier analysis for valid closed requests
        st.divider()
        st.header("Step 10 - IQR Outlier Analysis")
        st.write("Identify unusually long resolution times using the 1.5 × IQR rule.")

        if resolution_df.empty:
            st.warning("No valid closed requests are available for outlier analysis.")
        else:
            sorted_hours = resolution_df["resolution_hours"].sort_values().reset_index(drop=True)
            n = len(sorted_hours)
            # Nearest-rank quartiles, consistent with a SQL ROW_NUMBER approach.
            q1 = float(sorted_hours.iloc[(n + 3) // 4 - 1])
            q3 = float(sorted_hours.iloc[(3 * n + 3) // 4 - 1])
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            outlier_count = int((sorted_hours > upper_bound).sum())
            normal_count = n - outlier_count
            outlier_pct = 100 * outlier_count / n

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Valid Closed Requests", f"{n:,}")
            o2.metric("IQR", f"{iqr:.2f} hrs")
            o3.metric("Upper Outlier Threshold", f"{upper_bound:.2f} hrs")
            o4.metric("Outlier Requests", f"{outlier_count:,} ({outlier_pct:.2f}%)")

            outlier_summary = pd.DataFrame({
                "resolution_group": ["Within threshold", "Above threshold (outliers)"],
                "total_requests": [normal_count, outlier_count],
            })
            outlier_fig = px.bar(
                outlier_summary,
                x="resolution_group",
                y="total_requests",
                color="resolution_group",
                text="total_requests",
                title="Closed Requests: Normal vs IQR Outliers",
                labels={"resolution_group": "Resolution Group",
                        "total_requests": "Closed Requests"},
            )
            outlier_fig.update_layout(showlegend=False, height=450)
            outlier_fig.update_traces(textposition="outside")
            st.plotly_chart(outlier_fig, use_container_width=True)

            st.subheader("IQR Outlier Summary")
            st.dataframe(outlier_summary, use_container_width=True, hide_index=True)
            st.caption(f"Q1: {q1:.2f} hours | Q3: {q3:.2f} hours | "
                       f"IQR: {iqr:.2f} hours | Upper bound: {upper_bound:.2f} hours")
            st.info(f"{outlier_count:,} of {n:,} valid closed requests "
                    f"({outlier_pct:.2f}%) took longer than {upper_bound:.2f} hours.")

        # STEP 11: Resolution-time skewness (valid closed requests)
        st.divider()
        st.header("Step 11 - Resolution-Time Skewness")
        st.write("Measure whether resolution times have a long right or left tail.")

        if len(resolution_df) < 3:
            st.warning("At least three valid resolution times are needed for skewness analysis.")
        else:
            hours = resolution_df["resolution_hours"]
            mean_hours = float(hours.mean())
            median_hours = float(hours.median())
            std_hours = float(hours.std(ddof=0))
            skewness = float(((hours - mean_hours) ** 3).mean() / (std_hours ** 3)) if std_hours > 0 else 0.0

            sk1, sk2, sk3, sk4 = st.columns(4)
            sk1.metric("Valid Closed Requests", f"{len(hours):,}")
            sk2.metric("Mean Resolution", f"{mean_hours:.2f} hrs")
            sk3.metric("Median Resolution", f"{median_hours:.2f} hrs")
            sk4.metric("Population Skewness", f"{skewness:.4f}")

            st.subheader("Resolution Time Distribution")
            skew_fig = px.histogram(
                resolution_df,
                x="resolution_hours",
                nbins=50,
                title="Distribution of Closed-Request Resolution Times",
                labels={"resolution_hours": "Resolution Time (hours)"},
            )
            skew_fig.update_layout(yaxis_title="Closed Requests", height=450)
            st.plotly_chart(skew_fig, use_container_width=True)

            if skewness > 0:
                st.info("The distribution is positively skewed: longer resolution times form a right tail.")
            elif skewness < 0:
                st.info("The distribution is negatively skewed: shorter resolution times form a left tail.")
            else:
                st.info("The distribution has approximately zero skewness.")


        # STEP 12: Final insights and recommendations
        st.divider()
        st.header("Step 12 - Final Insights and Recommendations")
        st.write("Summary of observed patterns in the loaded NYC 311 sample.")

        top_complaint = complaint_df.iloc[0] if not complaint_df.empty else None
        top_agency = agency_df.iloc[0] if not agency_df.empty else None
        st.subheader("Key Findings")
        st.markdown(
            f"- **Complaint volume:** {total_requests:,} requests; "
            f"{closed_requests:,} marked Closed ({closure_rate:.2f}%).\n"
            f"- **Not marked Closed:** {total_requests - closed_requests:,} requests.\n"
            f"- **Typical resolution:** median {median_resolution:.2f} hours "
            f"versus mean {average_resolution:.2f} hours among valid closed requests.\n"
            f"- **Long resolutions:** {resolved_after_72:.2f}% of valid closed "
            f"requests exceeded 72 hours (an illustrative analytical threshold)."
        )
        if top_complaint is not None:
            st.write(
                f"Most reported complaint type: **{top_complaint['complaint_type']}** "
                f"({int(top_complaint['total_requests']):,} requests)."
            )
        if not borough_df.empty:
            busiest_borough = borough_df.sort_values('total_requests', ascending=False).iloc[0]
            st.write(
                f"Highest recorded complaint volume by borough: "
                f"**{busiest_borough['borough']}** "
                f"({int(busiest_borough['total_requests']):,} requests)."
            )
        if top_agency is not None:
            st.write(
                f"Agency with the most recorded requests: **{top_agency['agency']}** "
                f"({int(top_agency['total_requests']):,} requests)."
            )
        if not resolution_df.empty:
            st.write(
                f"**Resolution-time distribution:** skewness {skewness:.4f}; "
                f"{outlier_count:,} valid closed requests "
                f"({outlier_pct:.2f}%) exceeded the IQR upper bound of "
                f"{upper_bound:.2f} hours."
                if len(resolution_df) >= 3 else
                "Insufficient valid durations for skewness/outlier comparison."
            )

        st.subheader("Recommendations")
        st.markdown(
            "- Review high-volume complaint categories to prioritize staffing and triage.\n"
            "- Investigate unusually long resolution times and recurring delays.\n"
            "- Compare agencies with attention to differences in complaint types and case complexity.\n"
            "- Track closure and resolution trends over a longer period before drawing "
            "conclusions about sustained performance."
        )
        st.subheader("Limitations")
        st.caption(
            "311 requests represent reported issues, not every urban problem. "
            "Recorded closure does not prove citizen satisfaction or independently "
            "verified resolution. Results describe the extracted sample and may change "
            "with time; agency comparisons may reflect different case complexity. "
            "The 72-hour threshold is illustrative, not an official SLA."
        )

    except Exception as exc:
        st.error(f"Dashboard error: {exc}")
    finally:
        if engine is not None:
            engine.dispose()


