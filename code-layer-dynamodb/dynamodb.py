from boto3 import resource as boto3_resource
from os import environ as os_environ

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

dynamodb = boto3_resource("dynamodb")
dynamodb_table = dynamodb.Table(os_environ['AUTH_TABLE_NAME'])
