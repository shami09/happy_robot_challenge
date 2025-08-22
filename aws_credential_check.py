import boto3
session = boto3.Session()
print("Profile:", session.profile_name)
print("Region:", session.region_name)
creds = session.get_credentials().get_frozen_credentials()
print("Access Key:", creds.access_key)
