'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import os
import aws_encryption_sdk
from datetime import datetime, timedelta

kms_key_provider = aws_encryption_sdk.KMSMasterKeyProvider(key_ids=[
    os.environ['KMS_MASTER_KEY_ARN']
])

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

ssm = boto3.client('ssm')
parameter = ssm.get_parameter(
    # A slash is needed because the Slack client ID parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['SLACK_CLIENT_ID_SSM_NAME'],
    WithDecryption=True
)
CLIENT_ID = parameter['Parameter']['Value']

parameter = ssm.get_parameter(
    # A slash is needed because the Slack client secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['SLACK_CLIENT_SECRET_SSM_NAME'],
    WithDecryption=True
)
CLIENT_SECRET = parameter['Parameter']['Value']

# Let the team try DelaySay, but warn them to pay.
# Stop access to DelaySay this long after they authorize DelaySay.
FREE_TRIAL_PERIOD = timedelta(days=14)

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def encrypt_oauth_token(token):
    token_as_bytes = token.encode()
    encrypted_token, encryptor_header = aws_encryption_sdk.encrypt(
        source=token_as_bytes,
        key_provider=kms_key_provider
    )
    return encrypted_token


def add_user_to_dynamodb(user_id, token, team_id, team_name, enterprise_id,
                         create_time):
    assert user_id and token
    item = {
        'PK': "USER#" + user_id,
        'SK': "user",
        'token': encrypt_oauth_token(token),
        'team_id': team_id,
        'team_name': team_name,
        'enterprise_id': enterprise_id,
        'create_time': create_time
    }
    for key in list(item):
        if not item[key]:
            del item[key]
    table.put_item(Item=item)


def add_team_to_dynamodb(team_id, team_name, enterprise_id, create_time,
                         payment_expiration):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        }
    )
    if 'Item' in response:
        return
    item = {
        'PK': "TEAM#" + team_id,
        'SK': "team",
        'team_name': team_name,
        'enterprise_id': enterprise_id,
        'create_time': create_time,
        'payment_expiration': payment_expiration,
        'payment_plan': "trial"
    }
    for key in list(item):
        if not item[key]:
            del item[key]
    table.put_item(Item=item)


def build_response(res, err=None):
    if err:
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': "https://delaysay.com/add-failed/"
            }
        }
    elif res == "canceled":
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': "https://delaysay.com/add-canceled/"
            }
        }
    else:
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': "https://delaysay.com/add-success/"
            }
        }


def lambda_handler(event, context):
    code = event['queryStringParameters']['code']
    r = requests.post(
        url="https://slack.com/api/oauth.v2.access",
        data={
            'code': code
        },
        headers={
            'Content-Type': "application/x-www-form-urlencoded"
        },
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        raise Exception("requests.post failed")
    content = json.loads(r.content)
    if not content['ok']:
        raise Exception(
            content['error']
            + ". OAuth access failed. If you're testing, please click the"
            ' "Add to Slack" link in the project doc to see if it works there.'
            "\nAlso check here to find out what the error means:"
            "\nhttps://api.slack.com/methods/oauth.v2.access")
    token = content['authed_user']['access_token']
    user_id = content['authed_user']['id']
    team_id = content['team']['id']
    team_name = content['team']['name']
    enterprise = content['enterprise']
    if enterprise:
        enterprise_id = enterprise['id']
    else:
        enterprise_id = None
    create_time_as_string = datetime.utcnow().strftime(DATETIME_FORMAT)
    payment_expiration = create_time + FREE_TRIAL_PERIOD
    payment_expiration_as_string = payment_expiration.strftime(DATETIME_FORMAT)
    add_user_to_dynamodb(
        user_id, token, team_id, team_name, enterprise_id,
        create_time_as_string)
    add_team_to_dynamodb(
        team_id, team_name, enterprise_id, create_time_as_string,
        payment_expiration_as_string)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        if (event['queryStringParameters'].get('error') == "access_denied"):
            return build_response("canceled")
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        traceback.print_exc()
        return build_response("error", err)
