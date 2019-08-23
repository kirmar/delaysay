'''
Code based on https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
from delaysay_parser_lambda_function_info import parser_lambda_name
from urllib.parse import parse_qs


def respond(res):
    return {
        'statusCode': '200',
        'body': res,
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    print("event: " + json.dumps(event))
    
    params = parse_qs(event['body'])
    print("params: " + json.dumps(params))
    
    user_id = params['user_id'][0]
    channel_id = params['channel_id'][0]
    
    params['request_timestamp'] = (
        int(event['multiValueHeaders']['X-Slack-Request-Timestamp'][0]))
    client = boto3.client('lambda')
    client.invoke(
        ClientContext="DelaySay handler",
        FunctionName=parser_lambda_name,
        InvocationType="Event",
        Payload=json.dumps(params)
    )
    
    return respond(
        f"Hi, <@{user_id}>! This is DelaySay, reporting for duty."
        f"\nGive me a moment while I parse your request."
    )


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        print("~~~~~~~~~~")
        try:
            string = ""
            for param in event['body'].split("&"):
                string += "\nevent['body']: " + param
            print(string)
        except:
            try:
                print("event: " + json.dumps(event))
            except:
                print("event: " + str(event))
        print("~~~~~~~~~~")
        traceback.print_exc()
        print("~~~~~~~~~~")
        return respond(
            "Hi, there! Sorry, DelaySay is confused right now."
            "\nTry again later or rephrase your command?")
