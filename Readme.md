# HappyRobot – Inbound Carrier Sales Automation

This repository contains my implementation of the **Inbound Carrier Sales automation** challenge using the **HappyRobot platform**, AWS, and a custom dashboard in streamlit. It demonstrates automating carrier call workflows for a freight brokerage.


## Overview

The goal of this project is to automate **inbound carrier load sales**:

- Carriers call in requesting loads.
- The system authenticates them (via FMCSA API).
- Matches them to available loads from DynamoDB database table loads.
- Negotiates pricing automatically.
- Extracts key call insights and classifies **outcome** + **sentiment**.
- Provides a **real-time dashboard** for metrics and monitoring.

---

## Objective 1: Inbound Use Case

Key capabilities implemented:

1. **Carrier Authentication**
   - MC number validation via **FMCSA API**.
   - Only eligible carriers proceed to load booking.

2. **Load Search & Offer**
   - Loads stored in DynamoDB **Loads** and exposed via **Athena queries**.
   - Each load record contains:
     - `load_id`, `origin`, `destination`, `pickup_datetime`,  
       `delivery_datetime`, `equipment_type`, `weight`, `commodity_type`,  
       `miles`, `num_of_pieces`, `dimensions`, `loadboard_rate`, `notes`.

3. **Automated Negotiation**
   - Handles up to **3 back-and-forth counteroffers**.
   - Accepts if within thresholds, else declines.

4. **Call Classification**
   - Extracts structured data from conversation.
   - Tags **Booking Outcome** (Booked / Failed/ Success (if booked without negotiation)).
   - Tags **Carrier Sentiment** (Positive / Negative / Failure).

---

## Objective 2: Metrics Dashboard

A **Streamlit dashboard** provides live reporting:

- **Carrier Sentiment** distribution (pie chart).
- **Booking Outcome** analysis (pie chart + KPIs).
- **Loadboard vs Accepted Rates** comparison with % variation.
- **Miles vs Rate Analysis**:
  - Scatter plots of distance vs. loadboard/accepted rates.
  - Rate difference by miles.

Tech:  
- `pandas` + `pyathena` for data access.  
- `plotly` for interactive visualizations.  
- `streamlit` for UI.
(Please refer requirements.txt)  

---

## Objective 3: Deployment & Infrastructure

- **Containerized with Docker**  
  Multi-service container running:
  - AWS Lambda functions (webhook + FMCSA integration).
  - Streamlit dashboard.  
  Managed via **Supervisor** inside Docker.

- **AWS Services**:
  - DynamoDB (loads DB).
  - Athena (analytics query layer).
  - S3 (query results staging + exports).
  - Lambda Function URL (API endpoint for HappyRobot webhook).

- **Security**:
  - HTTPS-ready.
  - Supports API Key authentication.

---

## This repo contains:

- **Working POC**: Lambda + Streamlit dashboard inside Docker. Streamlit dashboard can be access here: http://dashboard-elb-86171610.us-east-2.elb.amazonaws.com/.    
- **Dashboard Code**: Accessible on this link: https://happyrobotchallenge-idjqm3mqnajmbmz8qymfk2.streamlit.app/.  
- **Inbound Campaign Setup**: Configured in HappyRobot (via web call trigger).  


---

-happyRobot folder contains the final lambda function code for where the HappyRobot interface extracts data and write it to DynamoDB including the sentiment and call outcome.


