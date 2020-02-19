'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import os
from DelaySayStripeCheckoutExceptions import (
    TeamNotInDynamoDBError, NoTeamIdGivenError)
from datetime import datetime, timedelta


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

parameter_name = os.environ['STRIPE_CHECKOUT_SIGNING_SECRET_SSM_NAME']
print(parameter_name)

ssm = boto3.client('ssm')
parameter = ssm.get_parameter(
    Name=parameter_name,
    WithDecryption=True
)
stripe_signature = parameter['Parameter']['Value']

# Let the team use DelaySay this long after they pay.
SUBSCRIPTION_PERIOD = timedelta(days=30)


def update_payment_expiration(team_id, payment_expiration):
    assert team_id and payment_expiration
    response = table.update_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        },
        UpdateExpression="SET payment_expiration = :val",
        ExpressionAttributeValues={
            ':val': payment_expiration
        },
        ReturnValues="UPDATED_NEW"
    )
    if 'Item' not in response:
        raise TeamNotInDynamoDBError("Team did not authorize")


def build_response(res, err=None):
    if err:
        return {
            'statusCode': "405",
            'body': res,
            'headers': {
                'Content-Type': "application/json"
            }
        }
    else:
        return {
            'statusCode': "200",
            'body': res,
            'headers': {
                'Content-Type': "application/json"
            }
        }


def lambda_handler(event, context):
    print("event keys: ", list(event))
    print("context keys: ", list(context))
    
    team = event['queryStringParameters']['team']
    if not team:
        raise NoTeamIdGivenError("No team ID provided")
    now = datetime.utcnow()
    payment_expiration = now + SUBSCRIPTION_PERIOD
    update_payment_expiration(team_id, payment_expiration)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        traceback.print_exc()
        return build_response("error", err)
