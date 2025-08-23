import streamlit as st
import pandas as pd
from pyathena import connect
import plotly.express as px
import plotly.graph_objects as go

# ==========================
# Athena Connection
# ==========================
conn = connect(
    s3_staging_dir="s3://happyrobot-queryoutput/",
    region_name="us-east-2",
    catalog_name="dynamodb_loadoffers",
    schema_name="default",
    work_group="primary"
)

# ==========================
# Query Data
# ==========================
query = """
SELECT * 
FROM "default"."loadoffers" 
WHERE mcnumber IS NOT NULL AND mcnumber <> ''
LIMIT 500;
"""
df = pd.read_sql(query, conn)

# ==========================
# Dashboard Title
# ==========================
st.title("📊 Loadoffers Dashboard")
st.write("This dashboard provides an overview of load offers, rates, booking success, carrier sentiment, and negotiation trends.")

# =========================================================
# 1. Aggregated Loadboard vs Accepted Rate (by Origin State)
# =========================================================

def get_state(location):
    if pd.isna(location):
        return None
    parts = location.split(",")
    return parts[-1].strip() if len(parts) > 1 else None

df["origin_state"] = df["origin"].apply(get_state)
df["destination_state"] = df["destination"].apply(get_state)

if "accepted_loadrate" in df.columns and "loadboard_rate" in df.columns:
    df_grouped = (
        df.dropna(subset=["accepted_loadrate", "loadboard_rate", "origin_state"])
        .groupby("origin_state")
        .agg(
            avg_loadboard_rate=("loadboard_rate", "mean"),
            avg_accepted_rate=("accepted_loadrate", "mean"),
            count=("load_id", "count")
        )
        .reset_index()
    )

    # % change compared to loadboard
    df_grouped["pct_change"] = (
        (df_grouped["avg_accepted_rate"] - df_grouped["avg_loadboard_rate"])
        / df_grouped["avg_loadboard_rate"] * 100
    ).round(1)

    st.subheader("📈 Average Rates by Origin State")
    st.caption("Aggregated view: comparing average Loadboard vs Accepted rates for each origin state (with % change labels).")

    # Keep Plotly default colors
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=df_grouped["origin_state"], 
        y=df_grouped["avg_loadboard_rate"], 
        name="Loadboard Rate"
    ))
    fig1.add_trace(go.Bar(
        x=df_grouped["origin_state"], 
        y=df_grouped["avg_accepted_rate"], 
        name="Accepted Rate"
    ))

    # Add % change labels above Accepted bars
    for i, row in df_grouped.iterrows():
        color = "skyblue" if row["pct_change"] > 0 else "red"
        fig1.add_annotation(
            x=row["origin_state"],
            y=row["avg_accepted_rate"] + (0.02 * row["avg_accepted_rate"]),  # offset above bar
            text=f"{row['pct_change']}%",
            showarrow=False,
            font=dict(size=12, color=color, family="Arial Black"),
            align="center"
        )

    fig1.update_layout(
        barmode="group",
        xaxis_title="Origin State",
        yaxis_title="Average Rate",
        title="Average Loadboard vs Accepted Rates by Origin State"
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning("accepted_loadrate or loadboard_rate column not found in data.")


# =====================================================
# 2 & 3. Carrier Sentiment + Booking Outcome (Side by Side)
# =====================================================
# =====================================================
# 2 & 3. Carrier Sentiment + Booking Outcome (Side by Side)
# =====================================================
col1, col2 = st.columns([1, 1])

with col1:
    if "carrier_sentiment" in df.columns:
        st.subheader("😊 Carrier Sentiment")
        sentiment_counts = df["carrier_sentiment"].value_counts()
        fig2 = px.pie(
            names=sentiment_counts.index,
            values=sentiment_counts.values,
            hole=0.4,
            title="Carrier Sentiment",
            color=sentiment_counts.index,
            color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "gray"}
        )
        st.plotly_chart(fig2, use_container_width=True)

with col2:
    if "call_outcome" in df.columns and "accepted_loadrate" in df.columns and "loadboard_rate" in df.columns:
        st.subheader("☎️ Booking Outcome")

        total_items = len(df)

        # Normalize outcomes to lowercase
        df["call_outcome"] = df["call_outcome"].str.lower()

        # Success without negotiation:
        success_mask = (df["call_outcome"] == "success") | (
            (df["call_outcome"] == "booked") & (df["accepted_loadrate"] == df["loadboard_rate"])
        )
        success_no_negotiation = df[success_mask]

        # Booked with negotiation:
        booked_with_negotiation = df[
            (df["call_outcome"] == "booked") & (df["accepted_loadrate"] != df["loadboard_rate"])
        ]

        # Not booked:
        not_booked = df[~(success_mask | (df["call_outcome"] == "booked"))]

        success_count = len(success_no_negotiation)
        booked_count = len(booked_with_negotiation)
        not_booked_count = len(not_booked)

        # Pie chart
        fig3 = px.pie(
            values=[success_count, booked_count, not_booked_count],
            names=["Success (No Negotiation)", "Booked (Negotiated)", "Not Booked"],
            hole=0.5,
            title="Booking Outcome Breakdown",
            color=["Success (No Negotiation)", "Booked (Negotiated)", "Not Booked"],
            color_discrete_map={
                "Success (No Negotiation)": "green",
                "Booked (Negotiated)": "orange",
                "Not Booked": "red"
            }
        )
        fig3.update_layout(showlegend=True)
        st.plotly_chart(fig3, use_container_width=True)

        # Metrics
        st.metric("Total Calls", total_items)
        st.metric("Success (No Negotiation)", success_count)
        st.metric("Booked (Negotiated)", booked_count)
        st.metric("Not Booked", not_booked_count)
        st.metric(
            "Call Success Rate",
            f"{(success_count+booked_count)}/{total_items} ({((success_count+booked_count)/total_items*100):.1f}%)"
        )


# =====================================================
# 4. Rates vs Miles (Multi-Line Chart)
# =====================================================
# =====================================================
# 4. Rates vs Miles (Multi-Line Chart + Difference Line Chart)
# =====================================================
if "miles" in df.columns and "loadboard_rate" in df.columns and "accepted_loadrate" in df.columns:
    st.subheader("🚚 Rates vs Miles")
    st.caption("First chart: compares Loadboard and Accepted rates across distance (miles). Second chart: shows the difference (Accepted − Loadboard).")

    df_miles = df.dropna(subset=["miles", "loadboard_rate", "accepted_loadrate"]).copy()
    df_miles_sorted = df_miles.sort_values("miles")

    # Multi-line chart (Miles vs Loadboard & Accepted)
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df_miles_sorted["miles"], y=df_miles_sorted["loadboard_rate"],
        mode="lines+markers", name="Loadboard Rate", line=dict(color="blue")
    ))
    fig4.add_trace(go.Scatter(
        x=df_miles_sorted["miles"], y=df_miles_sorted["accepted_loadrate"],
        mode="lines+markers", name="Accepted Rate", line=dict(color="red")
    ))
    fig4.update_layout(
        title="Rates vs Miles",
        xaxis_title="Miles",
        yaxis_title="Rate",
        height=500
    )
    st.plotly_chart(fig4, use_container_width=True)

    # Difference line chart (Miles vs Accepted − Loadboard)
    df_miles_sorted["rate_diff"] = df_miles_sorted["accepted_loadrate"] - df_miles_sorted["loadboard_rate"]

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=df_miles_sorted["miles"], y=df_miles_sorted["rate_diff"],
        mode="lines+markers", name="Rate Difference", line=dict(color="purple")
    ))
    fig5.update_layout(
        title="Difference vs Miles (Accepted − Loadboard)",
        xaxis_title="Miles",
        yaxis_title="Rate Difference",
        height=500
    )
    st.plotly_chart(fig5, use_container_width=True)

# =====================================================
# 5. Call Duration Insights (Custom Buckets in Minutes)
# =====================================================
if "call_duration" in df.columns:
    st.subheader("⏱ Impact of Call Duration")
    st.caption("How negotiation time (call duration) affects booking success rate and rate differences.")

    # Ensure numeric duration
    df["call_duration"] = pd.to_numeric(df["call_duration"], errors="coerce")

    # Define buckets (seconds → minutes)
    def bucket_duration(seconds):
        if pd.isna(seconds):
            return None
        minutes = seconds / 60
        if minutes < 1:
            return "Very Short (<1 min)"
        elif minutes < 4:
            return "Short (1–4 mins)"
        elif minutes < 7:
            return "Medium (4–7 mins)"
        else:
            return "Long (7+ mins)"

    df["call_duration_bucket"] = df["call_duration"].apply(bucket_duration)

    # Aggregate success rate & avg diff
    success_by_duration = df.groupby("call_duration_bucket").agg(
        success_rate=("call_outcome", lambda x: (x.str.lower()=="booked").mean()*100),
        avg_rate_diff=("accepted_loadrate", lambda x: (x - df.loc[x.index, "loadboard_rate"]).mean()),
        count=("call_outcome", "size")  # number of calls per bucket
    ).reset_index()

    # Define desired order
    bucket_order = ["Very Short (<1 min)", "Short (1–4 mins)", "Medium (4–7 mins)", "Long (7+ mins)"]

    # Reindex to ensure all buckets appear
    success_by_duration = success_by_duration.set_index("call_duration_bucket").reindex(bucket_order).reset_index()

    # Fill missing buckets with 0
    success_by_duration = success_by_duration.fillna(0)

    # ✅ Success rate chart
    fig6 = px.bar(
        success_by_duration,
        x="call_duration_bucket",
        y="success_rate",
        title="Booking Success Rate by Call Duration",
        category_orders={"call_duration_bucket": bucket_order},
        color="call_duration_bucket",
        text="count"  # add count labels on bars
    )
    fig6.update_traces(texttemplate="%{text:.0f} calls", textposition="outside")
    st.plotly_chart(fig6, use_container_width=True)

    # ✅ Rate difference chart
    fig7 = px.bar(
        success_by_duration,
        x="call_duration_bucket",
        y="avg_rate_diff",
        title="Average Accepted−Loadboard Rate by Call Duration",
        category_orders={"call_duration_bucket": bucket_order},
        color="call_duration_bucket",
        text="count"
    )
    fig7.update_traces(texttemplate="%{text:.0f} calls", textposition="outside")
    st.plotly_chart(fig7, use_container_width=True)

# =====================================================
# 6. Raw Data at Bottom (Reference Only)
# =====================================================
st.subheader(" Data Preview")
st.dataframe(df.head(100))
