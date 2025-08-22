import streamlit as st
import pandas as pd
from pyathena import connect
import plotly.express as px

# Athena connection
conn = connect(
    s3_staging_dir="s3://happyrobot-queryoutput/",
    region_name="us-east-2",
    catalog_name="dynamodb_loadoffers",   # match Data Source name in console
    schema_name="default",                # Database (default)
    work_group="primary"                  # same workgroup as in console
)

# Only return rows where mcnumber is not null and not empty
query = """
SELECT * 
FROM "default"."loadoffers" 
WHERE mcnumber IS NOT NULL AND mcnumber <> ''
LIMIT 50;
"""
df = pd.read_sql(query, conn)

st.title("Loadoffers Dashboard")
st.dataframe(df)

# ==========================
# Rate Difference Visualization
# ==========================
if "accepted_loadrate" in df.columns and "loadboard_rate" in df.columns:
    df["rate_diff"] = df["accepted_loadrate"] - df["loadboard_rate"]

    st.subheader("Difference between Accepted Loadrate and Loadboard Rate")
    st.bar_chart(df[["accepted_loadrate", "loadboard_rate", "rate_diff"]])

    st.subheader("Rate Difference Only")
    st.bar_chart(df["rate_diff"])
else:
    st.warning("accepted_loadrate or loadboard_rate column not found in data.")

# ==========================
# Carrier Sentiment Visualization
# ==========================
if "carrier_sentiment" in df.columns:
    st.subheader("Carrier Sentiment Distribution")

    sentiment_counts = df["carrier_sentiment"].value_counts()

    fig = px.pie(
        names=sentiment_counts.index,
        values=sentiment_counts.values,
        title="Carrier Sentiment",
        color=sentiment_counts.index,
        color_discrete_map={
            "Positive": "green",
            "Negative": "red",
            "Neutral": "gray"
        }
    )
    st.plotly_chart(fig)
else:
    st.warning("carrier_sentiment column not found in data.")
