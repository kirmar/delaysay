'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
# import os
from urllib.parse import parse_qs
from SlashCommandParser import SlashCommandParser, CommandParseError
from datetime import datetime, timezone, timedelta


def get_user_auth_token(user_id):
    dynamodb = boto3.resource("dynamodb")
    # TODO: Figure out how to do this:
    # table = dynamodb.Table(os.environ("AUTH_TABLE_NAME"))
    # Or remove the environment variable from template.yaml
    table = dynamodb.Table("User")
    response = table.get_item(
        Key={
            'id': user_id
        }
    )
    try:
        return response['Item']['token']
    except KeyError:
        raise Exception("User did not authenticate")


def get_user_timezone(user_id, token):
    r = requests.post(
        url="https://slack.com/api/users.info",
        data={
            'user': user_id
        },
        headers={
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': "Bearer " + token
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        raise Exception("requests.post failed")
    tz_offset = json.loads(r.content)['user']['tz_offset']
    user_tz = timezone(timedelta(seconds=tz_offset))
    return user_tz


def post_and_print_info_and_confirm_success(response_url, text):
    r = requests.post(
        url=response_url,
        json={
            'text': text
        },
        headers={
            'Content-Type': "application/json"
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        print(r.text)
        raise Exception("requests.post failed")
    return r


def parse_and_schedule(params):
    user = params['user_name'][0]
    user_id = params['user_id'][0]
    command = params['command'][0]
    command_text = params['text'][0]
    response_url = params['response_url'][0]
    
    token = get_user_auth_token(user_id)
    user_tz = get_user_timezone(user_id, token)
    
    request_unix_timestamp = params['request_timestamp']
    request_time = "<!date^" + str(request_unix_timestamp) + "^{time_secs}|"
    request_time += (
        datetime.utcfromtimestamp(request_unix_timestamp)
        .strftime("%H:%M:%S")
        + " UTC")
    request_time += ">"
    
    try:
        parser = SlashCommandParser(
            command_text,
            datetime.fromtimestamp(request_unix_timestamp, tz=user_tz))
    except CommandParseError:
        post_and_print_info_and_confirm_success(
            response_url,
            f"\nSorry, I can't parse the request you made at {request_time}:"
            f"\n`{command} {command_text}`")
        return
    
    date = parser.get_date_string_for_slack()
    time = parser.get_time_string_for_slack()
    message = parser.get_message()
    
    post_and_print_info_and_confirm_success(
        response_url,
        f"At {request_time}, you said:"
        f"\n`{command} {command_text}`"
        f'\nI will post "{message}" on your behalf at {time} on {date}.')


def build_response(res):
    return {
        'statusCode': "200",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
        }
    }


def respond_before_timeout(event, context):
    # Don't print the event or params, because they have secrets.
    # Or print only the keys.
    params = parse_qs(event['body'])
    user_id = params['user_id'][0]
    channel_id = params['channel_id'][0]
    
    params['request_timestamp'] = (
        int(event['multiValueHeaders']['X-Slack-Request-Timestamp'][0]))
    params['parser/scheduler'] = True
    client = boto3.client('lambda')
    client.invoke(
        ClientContext="DelaySay handler",
        FunctionName=context.function_name,
        InvocationType="Event",
        Payload=json.dumps(params)
    )
    
    return build_response(
        f"Hi, <@{user_id}>! This is DelaySay, reporting for duty."
        f"\nGive me a moment while I parse your request."
    )


def lambda_handler(event, context):
    if "parser/scheduler" in event:
        print("~~~   PARSER / SCHEDULER   ~~~")
        return parse_and_schedule(event)
    else:
        print("~~~   FIRST RESPONDER BEFORE TIMEOUT   ~~~")
        return respond_before_timeout(event, context)


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the message parsed by SlashCommandParser.
        traceback.print_exc()
        return build_response(
            "Hi, there! Sorry, DelaySay is confused right now."
            "\nTry again later or rephrase your command?")
