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
# Dashboard Title & Preview
# ==========================
st.title("📊 Loadoffers Dashboard")
st.write("This dashboard provides an overview of load offers, rate differences, carrier sentiment, booking outcomes, and trends across miles.")

st.dataframe(df.head(50))  # preview first 50 records

# ==========================
# 1. Loadboard vs Accepted Loadrate + % Variation
# ==========================
if "accepted_loadrate" in df.columns and "loadboard_rate" in df.columns:
    # ✅ Drop rows with missing values in either rate column
    df_rates = df.dropna(subset=["accepted_loadrate", "loadboard_rate"]).copy()

    df_rates["rate_diff"] = df_rates["accepted_loadrate"] - df_rates["loadboard_rate"]
    df_rates["rate_pct_var"] = (
        (df_rates["accepted_loadrate"] - df_rates["loadboard_rate"]) 
        / df_rates["loadboard_rate"] * 100
    ).round(2)

    st.subheader("📈 Loadboard vs Accepted Loadrate")
    st.caption("Comparison of offered vs accepted rates, with percentage variation for each record.")

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df_rates.index, y=df_rates["loadboard_rate"], name="Loadboard Rate"))
    fig1.add_trace(go.Bar(x=df_rates.index, y=df_rates["accepted_loadrate"], name="Accepted Loadrate"))

    # % variation labels
    for i, pct in enumerate(df_rates["rate_pct_var"]):
        fig1.add_annotation(
            x=df_rates.index[i],
            y=max(df_rates["loadboard_rate"].iloc[i], df_rates["accepted_loadrate"].iloc[i]) + 200,
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
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning("accepted_loadrate or loadboard_rate column not found in data.")

# ==========================
# 2 & 3. Carrier Sentiment + Booking Outcome (Side by Side)
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

        c1, c2 = st.columns([2, 1.5])  # left: chart, right: metrics

        with c1:
            fig3 = px.pie(
                values=[booked_items, not_booked],
                names=["Booked", "Not Booked"],
                hole=0.5,
                title="Booked vs Not Booked",
                color=["Booked", "Not Booked"],
                color_discrete_map={"Booked": "green", "Not Booked": "red"}
            )
            fig3.update_layout(
                margin=dict(l=20, r=5, t=10, b=10),
                showlegend=True)
            st.plotly_chart(fig3, use_container_width=True)

        with c2:
            st.metric("Total Calls", total_items)
            st.metric("Booked", booked_items)
            st.metric("% Booked", f"{(booked_items / total_items * 100):.2f} %")
    else:
        st.warning("call_outcome column not found in data.")


# ==========================
# 4 & 5. Miles vs Rates (Side by Side, Fixed Legends & Widths)
# ==========================
if "miles" in df.columns and "loadboard_rate" in df.columns and "accepted_loadrate" in df.columns:
    st.subheader("🚚 Miles vs Rates Analysis")
    st.caption("Explore how rates change with distance. The left chart compares raw Loadboard vs Accepted rates, while the right chart highlights the difference between them.")

    # ✅ Drop rows where miles or either rate is missing
    df_miles = df.dropna(subset=["miles", "loadboard_rate", "accepted_loadrate"]).copy()

    # ---------- Option 1: Miles vs Rates (Combined Scatter) ----------
    df_melted = df_miles.melt(
        id_vars=["miles"],
        value_vars=["loadboard_rate", "accepted_loadrate"],
        var_name="Rate Type",
        value_name="Rate"
    )

    fig4 = px.scatter(
        df_melted,
        x="miles",
        y="Rate",
        color="Rate Type",
        title="Miles vs Loadboard & Accepted Rates",
        color_discrete_map={
            "loadboard_rate": "blue",
            "accepted_loadrate": "red"
        },
        opacity=0.7
    )
    fig4.update_traces(marker=dict(size=10))
    fig4.update_layout(
        legend=dict(
            orientation="h",         # horizontal layout
            yanchor="top",
            y=-0.35,                 # push further down to avoid overlapping x-axis
            xanchor="center",
            x=0.5,
            title=None               # remove "Rate Type" title
        ),
        margin=dict(l=50, r=50, t=60, b=100),  # extra bottom space for legend
        height=500
    )

    # ---------- Option 2: Rate Difference vs Miles ----------
    df_miles["rate_diff"] = df_miles["accepted_loadrate"] - df_miles["loadboard_rate"]

    fig5 = px.scatter(
        df_miles,
        x="miles",
        y="rate_diff",
        title="Miles vs Rate Difference (Accepted − Loadboard)",
        color_discrete_sequence=["purple"],
        opacity=0.7
    )
    fig5.update_traces(marker=dict(size=10))
    fig5.update_layout(
        margin=dict(l=50, r=50, t=60, b=60),
        yaxis_title="Rate Difference",
        height=500
    )

    # ---------- Side-by-side display with wider layout ----------
    col_a, col_b = st.columns([1, 1])  # equally wide but full use of container

    with col_a:
        st.subheader("📊 Miles vs Rates")
        st.caption("Direct comparison of Loadboard (blue) and Accepted (red) rates as miles increase.")
        st.plotly_chart(fig4, use_container_width=True)

    with col_b:
        st.subheader("📉 Rate Difference by Miles")
        st.caption("Shows whether Accepted rates are higher or lower than Loadboard rates depending on trip distance.")
        st.plotly_chart(fig5, use_container_width=True)