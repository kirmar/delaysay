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

INSTALL_SUCCESS_URL = os.environ['INSTALL_SUCCESS_URL']
INSTALL_CANCEL_URL = os.environ['INSTALL_CANCEL_URL']
INSTALL_FAIL_URL = os.environ['INSTALL_FAIL_URL']

# Let the team try DelaySay, but warn them to pay.
# Stop access to DelaySay this long after they authorize DelaySay.
FREE_TRIAL_PERIOD = timedelta(days=14)


def build_response(res, err=None):
    if err:
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': INSTALL_FAIL_URL
            }
        }
    elif res == "canceled":
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': INSTALL_CANCEL_URL
            }
        }
    else:
        return {
            'statusCode': "302",
            'body': res,
            'headers': {
                'Content-Type': "application/json",
                'Location': INSTALL_SUCCESS_URL
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
    trial_expiration = create_time + FREE_TRIAL_PERIOD
    
    user = User(user_id)
    team = Team(team_id)
    user.add_to_dynamodb(token, team_id, team_name, enterprise_id, create_time)
    team.add_to_dynamodb(team_name, enterprise_id, create_time, trial_expiration)
    return build_response("success")


def lambda_handler_with_catch_all(event, context):
    try:
        if (event['queryStringParameters'].get('error') == "access_denied"):
            return build_response("canceled")
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        print(traceback.format_exc().replace('\n', '\r'))
        return build_response("error", err)
