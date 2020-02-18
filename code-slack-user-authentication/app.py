'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import os
from slack_app_info import CLIENT_ID, CLIENT_SECRET
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])


def add_user_to_dynamodb(user_id, token, team_id, team_name, enterprise_id, create_time):
    assert user_id and token
    item = {
        'PK': "USER#" + user_id,
        'SK': "user",
        'token': token,
        'team_id': team_id,
        'team_name': team_name,
        'enterprise_id': enterprise_id,
        'create_time': create_time
    }
    for key in list(item):
        if not item[key]:
            del item[key]
    table.put_item(Item=item)


def add_team_to_dynamodb(team_id, team_name, enterprise_id, create_time, replace_team=False):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        }
    )
    if not replace_team and 'Item' in response:
        return
    item = {
        'PK': "TEAM#" + team_id,
        'SK': "team",
        'team_name': team_name,
        'enterprise_id': enterprise_id,
        'create_time': create_time
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
        url="https://slack.com/api/oauth.access",
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code
        },
        headers={
            'Content-Type': "application/x-www-form-urlencoded"
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        raise Exception("requests.post failed")
    content = json.loads(r.content)
    if not content['ok']:
        raise Exception(
            content['error']
            + ". OAuth access failed. If you're testing, please click the"
            ' "Add to Slack" link in the project doc.')
    token = content['access_token']
    user_id = content['user_id']
    team_id = content['team_id']
    team_name = content['team_name']
    enterprise_id = content.get('enterprise_id', None)
    create_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    add_user_to_dynamodb(
        user_id, token, team_id, team_name, enterprise_id, create_time)
    add_team_to_dynamodb(team_id, team_name, enterprise_id, create_time)
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
