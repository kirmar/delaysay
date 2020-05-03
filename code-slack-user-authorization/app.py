'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import os
from User import User
from Team import Team
from datetime import datetime, timedelta

ssm = boto3.client('ssm')

slack_client_id_parameter = ssm.get_parameter(
    Name=os.environ['SLACK_CLIENT_ID_SSM_NAME'],
    WithDecryption=True
)
CLIENT_ID = slack_client_id_parameter['Parameter']['Value']

slack_client_secret_parameter = ssm.get_parameter(
    Name=os.environ['SLACK_CLIENT_SECRET_SSM_NAME'],
    WithDecryption=True
)
CLIENT_SECRET = slack_client_secret_parameter['Parameter']['Value']

# Let the team try DelaySay, but warn them to pay.
# Stop access to DelaySay this long after they authorize DelaySay.
FREE_TRIAL_PERIOD = timedelta(days=14)

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


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
    create_time = datetime.utcnow()
    create_time_as_string = create_time.strftime(DATETIME_FORMAT)
    payment_expiration = create_time + FREE_TRIAL_PERIOD
    payment_expiration_as_string = payment_expiration.strftime(DATETIME_FORMAT)
    
    user = User(user_id)
    user.add_to_dynamodb(token, team_id, team_name, enterprise_id,
                         create_time_as_string)
    team = Team(team_id)
    team.add_to_dynamodb(team_name, enterprise_id, create_time_as_string,
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
