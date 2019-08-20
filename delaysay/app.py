'''
Code based on https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
from SlashCommandParser import SlashCommandParser
from urllib.parse import parse_qs
from datetime import datetime

# import requests


def respond(res):
    return {
        'statusCode': '200',
        'body': res,
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
    user_id = params['user_id'][0]
    command = params['command'][0]
    channel = params['channel_name'][0]
    command_text = params['text'][0]
    
    parser = SlashCommandParser(command_text, initial_time=datetime.now())
    date = parser.get_date_string()
    time = parser.get_time_string()
    message = parser.get_message()
    
    return respond(
        f"Hi, <@{user_id}>! This is DelaySay, reporting for duty."
        f"\nYou said: `{command} {command_text}`"
        f'\nI will post "{message}" on your behalf at {time} on {date}.')


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
