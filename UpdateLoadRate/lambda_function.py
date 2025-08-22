import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table("LoadsTable")  # Replace with your DynamoDB table name

def lambda_handler(event, context):
    """
    event should contain: {
        "load_id": "12345",
        "accepted_loadrate": 1500
    }
    """
    load_id = event.get("load_id")
    accepted_loadrate = event.get("accepted_loadrate")

    if not load_id or accepted_loadrate is None:
        return {"status": "error", "message": "Missing load_id or accepted_loadrate"}

    try:
        # Update the item in DynamoDB with the accepted_loadrate field
        response = table.update_item(
            Key={"load_id": load_id},   # Ensure 'load_id' is your table's partition key
            UpdateExpression="SET accepted_loadrate = :val",
            ExpressionAttributeValues={":val": accepted_loadrate},
            ReturnValues="UPDATED_NEW"
        )

        return {
            "status": "success",
            "updated_attributes": response.get("Attributes", {})
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
