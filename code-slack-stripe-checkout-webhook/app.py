'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import os
import hashlib
import hmac
import time
from DelaySayStripeCheckoutExceptions import (
    TeamNotInDynamoDBError, NoTeamIdGivenError, SignaturesDoNotMatchError,
    TimeToleranceExceededError)
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

ssm = boto3.client('ssm')
parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_CHECKOUT_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
ENDPOINT_SECRET = parameter['Parameter']['Value']

# Let the team use DelaySay this long after they pay.
SUBSCRIPTION_PERIOD = timedelta(days=30)

# If the timestamp is this old, reject the payload.
# (https://stripe.com/docs/webhooks/signatures#replay-attacks)
TIME_TOLERANCE_IN_SECONDS = 5 * 60


def find_timestamp_and_signature(stripe_signature):
    received_timestamp = None
    received_signature = None
    for element in stripe_signature.split(","):
        prefix, value = element.split("=")
        if prefix == "t":
            received_timestamp = value
        if prefix == "v1":
            received_signature = value
        if received_timestamp and received_signature:
            return received_timestamp, received_signature
    raise Exception(
        "Stripe signature is missing timestamp and/or signature"
        "\nreceived_timestamp: " + received_timestamp +
        "\nreceived_signature: " + received_signature)


def compute_expected_signature(received_timestamp, payload):
    signed_payload = received_timestamp + "." + payload
    hash = hmac.new(
        key=ENDPOINT_SECRET.encode(),
        msg=signed_payload.encode(),
        digestmod=hashlib.sha256)
    expected_signature = hash.hexdigest()
    return expected_signature


def verify_stripe_signature(stripe_signature, payload):
    # https://stripe.com/docs/webhooks/signatures#verify-manually
    received_timestamp, received_signature = find_timestamp_and_signature(
        stripe_signature)
    expected_signature = compute_expected_signature(
        received_timestamp, payload)
    if received_signature != expected_signature:
        raise SignaturesDoNotMatchError("Stripe signatures do not match")
    current_timestamp = time.time()
    if float(current_timestamp) - float(received_timestamp) > TIME_TOLERANCE_IN_SECONDS:
        raise TimeToleranceExceededError(
            "Tolerance for timestamp difference was exceeded"
            "\ncurrent_timestamp: " + str(current_timestamp) +
            "\nreceived_timestamp: " + str(received_timestamp) +
            "\nTIME_TOLERANCE_IN_SECONDS: " + str(TIME_TOLERANCE_IN_SECONDS))


def confirm_team_exists(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        }
    )
    if 'Item' not in response:
        raise TeamNotInDynamoDBError("Team did not authorize: " + str(team_id))


def update_payment_expiration(team_id, payment_expiration):
    assert team_id and payment_expiration
    table.update_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        },
        UpdateExpression="SET payment_expiration = :val",
        ExpressionAttributeValues={
            ':val': payment_expiration
        }
    )


def build_response(res, err=None):
    if err:
        return {
            'statusCode': "500",
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
    stripe_signature = event['headers']['Stripe-Signature']
    verify_stripe_signature(stripe_signature, payload=event['body'])
    body = json.loads(event['body'])
    team_id = body['data']['object']['client_reference_id']
    if team_id == "no_team_id_provided":
        raise NoTeamIdGivenError("No team ID provided")
    confirm_team_exists(team_id)
    now = datetime.utcnow()
    payment_expiration = (now + SUBSCRIPTION_PERIOD).strftime("%Y-%m-%dT%H:%M:%SZ")
    update_payment_expiration(team_id, payment_expiration)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        traceback.print_exc()
        return build_response("error", err)
