import streamlit as st
import pandas as pd
from pyathena import connect
import plotly.express as px
import plotly.graph_objects as go

# ==========================
# Athena connection
# ==========================
conn = connect(
    s3_staging_dir="s3://happyrobot-queryoutput/",
    region_name="us-east-2",
    catalog_name="dynamodb_loadoffers",
    schema_name="default",
    work_group="primary"
)

# ==========================
# Query data
# ==========================
query = """
SELECT * 
FROM "default"."loadoffers" 
WHERE mcnumber IS NOT NULL AND mcnumber <> ''
LIMIT 500;
"""
df = pd.read_sql(query, conn)

st.title("📊 Loadoffers Dashboard")
st.write("This dashboard provides an overview of load offers, rate differences, carrier sentiment, booking outcomes, and trends across miles.")

st.dataframe(df)

# ==========================
# 1. Loadboard vs Accepted Loadrate + % Variation
# ==========================
if "accepted_loadrate" in df.columns and "loadboard_rate" in df.columns:
    df["rate_diff"] = df["accepted_loadrate"] - df["loadboard_rate"]
    df["rate_pct_var"] = (
        (df["accepted_loadrate"] - df["loadboard_rate"]) / df["loadboard_rate"] * 100
    ).round(2)

    st.subheader("📈 Loadboard vs Accepted Loadrate")
    st.caption("Comparison of offered vs accepted rates, with percentage variation for each record.")

    fig1 = go.Figure()
    # Default Plotly colors
    fig1.add_trace(go.Bar(x=df.index, y=df["loadboard_rate"], name="Loadboard Rate"))
    fig1.add_trace(go.Bar(x=df.index, y=df["accepted_loadrate"], name="Accepted Loadrate"))

    # % variation labels
    for i, pct in enumerate(df["rate_pct_var"]):
        fig1.add_annotation(
            x=i,
            y=max(df["loadboard_rate"].iloc[i], df["accepted_loadrate"].iloc[i]) + 200,
            text=f"{pct}%",
            showarrow=False,
            font=dict(color="white", size=11),
            align="center"
        )

    fig1.update_layout(
        barmode="group",
        xaxis_title="Records",
        yaxis_title="Rate",
        title="Loadboard vs Accepted Loadrate (with % Variation Labels)"
    )
    st.plotly_chart(fig1)
else:
    st.warning("accepted_loadrate or loadboard_rate column not found in data.")

# ==========================
# 2 & 3. Carrier Sentiment + Booking Outcome (Side by Side with spacing)
# ==========================
col1, spacer, col2 = st.columns([1, 0.1, 1])  # add spacing column

with col1:
    if "carrier_sentiment" in df.columns:
        st.subheader("😊 Carrier Sentiment")
        st.caption("Distribution of carrier sentiments expressed during interactions.")

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
    else:
        st.warning("carrier_sentiment column not found in data.")

with col2:
    if "call_outcome" in df.columns:
        st.subheader("☎️ Booking Outcome")
        st.caption("Proportion of calls that resulted in a booking compared to total calls.")

        total_items = len(df)
        booked_items = (df["call_outcome"].str.lower() == "booked").sum()
        not_booked = total_items - booked_items

        c1, c2 = st.columns([2, 1])  # left: chart, right: metrics

        with c1:
            fig3 = px.pie(
                values=[booked_items, not_booked],
                names=["Booked", "Not Booked"],
                hole=0.5,
                title="Booked vs Not Booked",
                color=["Booked", "Not Booked"],
                color_discrete_map={"Booked": "green", "Not Booked": "red"}
            )
            st.plotly_chart(fig3, use_container_width=True)

        with c2:
            st.metric("Total Calls", total_items)
            st.metric("Booked", booked_items)
            st.metric("% Booked", f"{(booked_items / total_items * 100):.2f} %")
    else:
        st.warning("call_outcome column not found in data.")

# ==========================
# 4 & 5. Miles vs Rates (Side by Side with spacing)
# ==========================
if "miles" in df.columns:
    st.subheader("🚚 Miles vs Rates")
    st.caption("Relationship between distance (miles) and rates offered (Loadboard) vs accepted (Carrier).")

    col1, spacer, col2 = st.columns([1, 0.1, 1])  # add spacing column

    if "loadboard_rate" in df.columns:
        with col1:
            fig4 = px.scatter(
                df,
                x="miles",
                y="loadboard_rate",
                trendline="ols",
                title="Miles vs Loadboard Rate",
                color_discrete_sequence=["blue"]
            )
            st.plotly_chart(fig4, use_container_width=True)

    if "accepted_loadrate" in df.columns:
        with col2:
            fig5 = px.scatter(
                df,
                x="miles",
                y="accepted_loadrate",
                trendline="ols",
                title="Miles vs Accepted Loadrate",
                color_discrete_sequence=["red"]
            )
            st.plotly_chart(fig5, use_container_width=True)
