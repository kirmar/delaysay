'''
Code based on https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import re
from SlashCommandParser import SlashCommandParser, TimeParseError
from datetime import datetime

import requests


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
        print(r.text)
        raise Exception("requests.post failed")
    return r


def lambda_handler(params, context):
    print("params: " + str(params))
    
    user = params['user_name'][0]
    user_id = params['user_id'][0]
    command = params['command'][0]
    command_text = params['text'][0]
    response_url = params['response_url'][0]
    
    request_timestamp = params['request_timestamp']
    request_time = "<!date^" + str(request_timestamp) + "^{time_secs}|"
    request_time += "HELP"
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
