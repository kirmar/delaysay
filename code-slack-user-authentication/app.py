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


def add_user_to_dynamodb(user_id, token, team_id, enterprise_id, create_time):
    item = {
        'id': user_id,
        'token': token,
        'team_id': team_id,
        'enterprise_id': enterprise_id,
        'create_time': create_time
    }
    for key in list(item):
        if not item[key]:
            del item[key]
    assert item['id'] and item['token']
    table.put_item(Item=item)


def build_response(res, err=None):
    return {
        'statusCode': "400" if err else "302",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
            'Location': "https://delaysay.com/added/"
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
        print("Error: " + content['error'])
        raise Exception(
            "OAuth access failed. If you're testing, please click the"
            ' "Add to Slack" link in the project doc.')
    token = content['access_token']
    user_id = content['user_id']
    team_id = content['team_id']
    enterprise_id = content.get('enterprise_id', None)
    create_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    add_user_to_dynamodb(user_id, token, team_id, enterprise_id, create_time)
    return build_response("Hello, world!")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        traceback.print_exc()
        return build_response("There was an error.", err)
