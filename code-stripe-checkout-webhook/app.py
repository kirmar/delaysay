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
from Team import Team
from DelaySayExceptions import (
    TeamNotInDynamoDBError, NoTeamIdGivenError, SignaturesDoNotMatchError,
    TimeToleranceExceededError)
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

ssm = boto3.client('ssm')

stripe_signing_secret_parameter = ssm.get_parameter(
    Name=os.environ['STRIPE_CHECKOUT_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
ENDPOINT_SECRET = stripe_signing_secret_parameter['Parameter']['Value']

stripe_test_signing_secret_parameter = ssm.get_parameter(
    Name=os.environ['STRIPE_TESTING_CHECKOUT_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
TEST_ENDPOINT_SECRET = stripe_test_signing_secret_parameter['Parameter']['Value']

# If the timestamp is this old, reject the payload.
# (https://stripe.com/docs/webhooks/signatures#replay-attacks)
TIME_TOLERANCE_IN_SECONDS = 5 * 60

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


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


def compute_expected_signature(received_timestamp, payload, is_live):
    signed_payload = received_timestamp + "." + payload
    if is_live:
        secret = ENDPOINT_SECRET
    else:
        secret = TEST_ENDPOINT_SECRET
    hash = hmac.new(
        key=secret.encode(),
        msg=signed_payload.encode(),
        digestmod=hashlib.sha256)
    expected_signature = hash.hexdigest()
    return expected_signature


def verify_stripe_signature(stripe_signature, payload, is_live):
    # https://stripe.com/docs/webhooks/signatures#verify-manually
    received_timestamp, received_signature = find_timestamp_and_signature(
        stripe_signature)
    expected_signature = compute_expected_signature(
        received_timestamp, payload, is_live)
    if received_signature != expected_signature:
        raise SignaturesDoNotMatchError("Stripe signatures do not match")
    current_timestamp = time.time()
    if float(current_timestamp) - float(received_timestamp) > TIME_TOLERANCE_IN_SECONDS:
        raise TimeToleranceExceededError(
            "Tolerance for timestamp difference was exceeded"
            "\ncurrent_timestamp: " + str(current_timestamp) +
            "\nreceived_timestamp: " + str(received_timestamp) +
            "\nTIME_TOLERANCE_IN_SECONDS: " + str(TIME_TOLERANCE_IN_SECONDS))


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
    payload = event['body']
    payload_json = json.loads(payload)
    is_live = payload_json['livemode']
    verify_stripe_signature(stripe_signature, payload=payload, is_live=is_live)
    object = payload_json['data']['object']
    team_id = object['client_reference_id']
    plan_name = object['display_items'][0]['plan']['nickname']
    if team_id == "no_team_id_provided":
        raise NoTeamIdGivenError("No team ID provided")
    
    team = Team(team_id)
    subscription_id = object['subscription']
    team.add_subscription(subscription_id)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        print(traceback.format_exc().replace('\n', '\r'))
        return build_response("error", err)
