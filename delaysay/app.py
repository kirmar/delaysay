'''
Code based on https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
from urllib.parse import parse_qs

# import requests


def respond(res):
    return {
        'statusCode': '200',
        'body': json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e
    
    print("event: " + json.dumps(event))
    
    params = parse_qs(event['body'])
    print("params: " + json.dumps(params))
    
    user = params['user_name'][0]
    command = params['command'][0]
    channel = params['channel_name'][0]
    command_text = params['text'][0]
    
    return respond(f"Hi, @{user}! This is DelaySay, reporting for duty.")


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        print("~~~~~~~~~~")
        print("\nevent['body']: ".join(event['body'].split("&")))
        print("~~~~~~~~~~")
        traceback.print_exc()
        print("~~~~~~~~~~")
        return respond(
            f"Hi, there! DelaySay is confused right now. Try again later?")