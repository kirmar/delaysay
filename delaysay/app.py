'''
Code based on https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import re
from SlashCommandParser import SlashCommandParser, TimeParseError
from datetime import datetime
from urllib.parse import parse_qs


def post_and_print_info_and_confirm_success(response_url, text):
    r = requests.post(
        url=response_url,
        json={
            'text': text
        },
        headers={
            'Content-Type': 'application/json"'
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        raise Exception("requests.post failed")
    return r


def parse_and_schedule(params):
    user = params['user_name'][0]
    user_id = params['user_id'][0]
    command = params['command'][0]
    command_text = params['text'][0]
    response_url = params['response_url'][0]
    
    request_unix_timestamp = params['request_timestamp']
    request_time = "<!date^" + str(request_unix_timestamp) + "^{time_secs}|"
    request_time += (
        datetime.utcfromtimestamp(request_unix_timestamp)
        .strftime("%H:%M:%S")
        + " UTC")
    request_time += ">"
    
    try:
        parser = SlashCommandParser(command_text, initial_time=datetime.now())
    except TimeParseError:
        post_and_print_info_and_confirm_success(
            response_url,
            f"\nSorry, I can't parse the request you made at {request_time}:"
            f"\n`{command} {command_text}`")
        return
    
    date = parser.get_date_string()
    time = parser.get_time_string()
    message = parser.get_message()
    
    post_and_print_info_and_confirm_success(
        response_url,
        f"At {request_time}, you said:"
        f"\n`{command} {command_text}`"
        f'\nI will post "{message}" on your behalf at {time} on {date}.')


def build_response(res):
    return {
        'statusCode': '200',
        'body': res,
        'headers': {
            'Content-Type': 'application/json',
        },
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
        return parse_and_schedule(event)
    else:
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
