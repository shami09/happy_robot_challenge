import os, json, base64
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal
from datetime import datetime

# DynamoDB table
TABLE_NAME = os.environ.get("TABLE_NAME", "loads")
ddb = boto3.resource("dynamodb").Table(TABLE_NAME)

# ---------- Config ----------
API_KEY = "PQR"

# ---------- Helpers ----------
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

def _parse_event(event):
    """Unwrap API Gateway/Lambda event -> Python dict with JSON body if present."""
    if not isinstance(event, dict):
        return {}
    body = event.get("body")
    if body is None:
        return event
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body) if isinstance(body, str) else body
    except Exception:
        return {}

def _city_only(s: str):
    return s.split(",")[0].strip().lower()

def _date_range(s: str):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        day = dt.date().isoformat()
    except Exception:
        day = s[:10]
    start = f"{day}T00:00:00Z"
    end   = f"{day}T23:59:59Z"
    return start, end

# ---------- Lambda handler ----------
def lambda_handler(event, context):
    # --- API Key Check ---
    qs_params = event.get("queryStringParameters", {}) or {}
    if qs_params.get("apikey") != API_KEY:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Unauthorized - invalid API key"})
        }

    # --- Parse body ---
    p = _parse_event(event)
    fe = Attr("load_id").exists()

    # Core fields
    if p.get("origin"):
        origin_city = _city_only(p["origin"])
        fe &= Attr("origin").contains(origin_city.title())
    if p.get("destination"):
        dest_city = _city_only(p["destination"])
        fe &= Attr("destination").contains(dest_city.title())

    if p.get("pickup_datetime"):
        start, end = _date_range(p["pickup_datetime"])
        fe &= Attr("pickup_datetime").between(start, end)

    if p.get("delivery_datetime"):
        start, end = _date_range(p["delivery_datetime"])
        fe &= Attr("delivery_datetime").between(start, end)

    # Optional fields
    if p.get("equipment_type"):
        fe &= Attr("equipment_type").eq(p["equipment_type"])
    if p.get("weight"):
        fe &= Attr("weight").lte(Decimal(str(p["weight"])))
    if p.get("commodity_type"):
        fe &= Attr("commodity_type").eq(p["commodity_type"])
    if p.get("num_of_pieces"):
        fe &= Attr("num_of_pieces").lte(int(p["num_of_pieces"]))
    if p.get("miles"):
        fe &= Attr("miles").lte(int(p["miles"]))
    if p.get("dimensions"):
        fe &= Attr("dimensions").eq(p["dimensions"])
    if p.get("loadboard_rate"):
        fe &= Attr("loadboard_rate").eq(Decimal(str(p["loadboard_rate"])))
    if p.get("notes"):
        fe &= Attr("notes").contains(p["notes"])


    # Scan DynamoDB
    resp = ddb.scan(FilterExpression=fe)
    items = resp.get("Items", [])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(items, cls=DecimalEncoder)
    }
