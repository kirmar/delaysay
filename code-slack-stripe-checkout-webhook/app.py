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
import stripe
from DelaySayStripeCheckoutExceptions import (
    TeamNotInDynamoDBError, NoTeamIdGivenError, SignaturesDoNotMatchError,
    TimeToleranceExceededError)
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

ssm = boto3.client('ssm')

stripe_signing_secret_parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_CHECKOUT_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
ENDPOINT_SECRET = stripe_signing_secret_parameter['Parameter']['Value']

stripe_api_key_parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_API_KEY_SSM_NAME'],
    WithDecryption=True
)
stripe.api_key = stripe_api_key_parameter['Parameter']['Value']

stripe_test_api_key_parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_TESTING_API_KEY_SSM_NAME'],
    WithDecryption=True
)
TEST_MODE_API_KEY = stripe_test_api_key_parameter['Parameter']['Value']


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


def get_payment_expiration_from_dynamodb(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
            }
    )
    expiration_string = response['Item']['payment_expiration']
    try:
        expiration = datetime.strptime(expiration_string, DATETIME_FORMAT)
        return expiration
    except:
        return expiration_string


def get_payment_plan_nickname_from_dynamodb(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
            }
    )
    payment_plan = response['Item']['payment_plan']
    return payment_plan


def get_payment_expiration_from_stripe(subscription_id):
    assert subscription_id
    try:
        subscription = stripe.Subscription.retrieve(self.id)
    except stripe.error.InvalidRequestError:
        subscription = stripe.Subscription.retrieve(
            self.id, api_key=TEST_MODE_API_KEY)
    expiration_unix_timestamp = subscription['current_period_end']
    expiration = datetime.utcfromtimestamp(expiration_unix_timestamp)
    return expiration


def update_payment_info(team_id, payment_expiration, payment_plan,
                        stripe_subscription_id):
    assert team_id and payment_expiration and payment_plan
    assert stripe_subscription_id
    table.update_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        },
        UpdateExpression="SET payment_expiration = :val,"
                         " payment_plan = :val2,"
                         " stripe_subscription_id = :val3",
        ExpressionAttributeValues={
            ":val": payment_expiration,
            ":val2": payment_plan,
            ":val3": stripe_subscription_id
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
    object = json.loads(event['body'])['data']['object']
    team_id = object['client_reference_id']
    plan_name = object['display_items'][0]['plan']['nickname']
    if team_id == "no_team_id_provided":
        raise NoTeamIdGivenError("No team ID provided")
    confirm_team_exists(team_id)
    
    # TODO: Is this the correct way to convert the Unix timestamp??
    subscription_id = object['subscription']
    expiration = get_payment_expiration_from_dynamodb(team_id)
    old_plan_name = get_payment_plan_nickname_from_dynamodb(team_id)
    if expiration == "never":
        # The team does not need to pay, because they are beta testers.
        # TODO: This program should immediately cancel the payment
        # and tell the user.
        expiration_string = expiration
    else:
        expiration_from_stripe = get_payment_expiration_from_stripe(
            subscription_id)
        if old_plan_name == "trial" or expiration_from_stripe > expiration:
            # TODO: If a team already has a longer subscription, this
            # program should immediately cancel the payment and tell them.
            expiration = expiration_from_stripe
        expiration_string = expiration.strftime(DATETIME_FORMAT)
    
    update_payment_info(team_id, expiration_string, plan_name, subscription_id)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        traceback.print_exc()
        return build_response("error", err)
