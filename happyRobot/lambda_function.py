import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("Loadoffers")

# --- Config ---
API_KEY = "sham_happyrobot"

def lambda_handler(event, context):
    # --- API Key Check ---
    qs_params = event.get("queryStringParameters", {}) or {}
    if qs_params.get("apikey") != API_KEY:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Unauthorized - invalid API key"})
        }

    # Parse request body if coming from Lambda Function URL
    if "body" in event:
        try:
            body = json.loads(event["body"])
        except Exception:
            body = {}
    else:
        body = event

    # If wrapped inside "data", unwrap it
    if isinstance(body, dict) and "data" in body:
        body = body["data"]

    # --- Helpers ---
    def as_str(val):
        return str(val) if val is not None else None

    def as_int(val):
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def as_double(val):
        try:
            return Decimal(str(val)) if val is not None else None
        except (ValueError, TypeError, ArithmeticError):
            return None

    # --- Normalize fields ---
    extracted_data = {
        "mcnumber": as_str(body.get("mcnumber")),
        "load_id": as_str(body.get("load_id")),
        "origin": as_str(body.get("origin")),
        "destination": as_str(body.get("destination")),
        "pickup_datetime": as_str(body.get("pickup_datetime")),
        "delivery_datetime": as_str(body.get("delivery_datetime")),
        "equipment_type": as_str(body.get("equipment_type")),
        "weight": as_str(body.get("weight")),
        "commodity_type": as_str(body.get("commodity_type")),
        "num_of_pieces": as_int(body.get("num_of_pieces")),
        "miles": as_int(body.get("miles")),
        "dimensions": as_str(body.get("dimensions")),
        "loadboard_rate": as_double(body.get("loadboard_rate")),
        "accepted_loadrate": as_double(body.get("accepted_loadrate")),
        "call_outcome": as_str(body.get("call_outcome")),
        "carrier_sentiment": as_str(body.get("carrier_sentiment")),
        "init_sentiment": as_str(body.get("init_sentiment")),
        "final_sentiment": as_str(body.get("final_sentiment")),
         "call_duration": as_int(body.get("call_duration")),
    }

    # --- Save to DynamoDB ---
    table.put_item(Item=extracted_data)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"message": "Saved to DynamoDB", "data": extracted_data},
            indent=2,
            default=str
        )
    }
