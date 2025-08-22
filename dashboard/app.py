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
# 4 & 5. Miles vs Rates (Better Comparison)
# ==========================
if "miles" in df.columns and "loadboard_rate" in df.columns and "accepted_loadrate" in df.columns:
    st.subheader("🚚 Miles vs Rates")
    st.caption("Visual comparison of Loadboard vs Accepted rates and their differences across distances.")

    # ---------- Option 1: Combined Scatter ----------
    df_melted = df.melt(
        id_vars=["miles"],
        value_vars=["loadboard_rate", "accepted_loadrate"],
        var_name="Rate Type",
        value_name="Rate"
    )

    fig1 = px.scatter(
        df_melted,
        x="miles",
        y="Rate",
        color="Rate Type",
        title="Miles vs Loadboard vs Accepted Loadrate",
        color_discrete_map={
            "loadboard_rate": "blue",
            "accepted_loadrate": "red"
        },
        opacity=0.7
    )
    fig1.update_traces(marker=dict(size=10))
    fig1.update_layout(legend_title_text="Rate Type")

    st.markdown("**Combined view:** Both Loadboard (blue) and Accepted (red) rates on the same chart for direct comparison.")
    st.plotly_chart(fig1, use_container_width=True)

    # ---------- Option 2: Difference vs Miles ----------
    df["rate_diff"] = df["accepted_loadrate"] - df["loadboard_rate"]

    fig2 = px.scatter(
        df,
        x="miles",
        y="rate_diff",
        title="Difference (Accepted − Loadboard) vs Miles",
        color_discrete_sequence=["purple"],
        opacity=0.7
    )
    fig2.update_traces(marker=dict(size=10))
    fig2.update_layout(yaxis_title="Rate Difference")

    st.markdown("**Difference view:** Highlights how much higher or lower Accepted rates are compared to Loadboard as miles increase.")
    st.plotly_chart(fig2, use_container_width=True)
