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


def add_user_to_dynamodb(user_id, token):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])
    table.put_item(
        Item={
            'id': user_id,
            'token': token
        }
    )


def build_response(res, err=None):
    return {
        'statusCode': "400" if err else "200",
        'body': str(err) if err else res,
        'headers': {
            'Content-Type': "application/json",
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
    add_user_to_dynamodb(user_id, token)
    return build_response("Hello, world!")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        traceback.print_exc()
        return build_response("There was an error.", err)
