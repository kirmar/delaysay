'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import slack
import os
import re
from urllib.parse import parse_qs
from SlashCommandParser import SlashCommandParser
from DelaySayExceptions import (
    UserAuthenticateError, CommandParseError, TimeParseError)
from datetime import datetime, timezone, timedelta
from random import sample

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])


def get_user_auth_token(user_id):
    response = table.get_item(
        Key={
            'id': user_id
        }
    )
    try:
        return response['Item']['token']
    except KeyError:
        raise UserAuthenticateError("User did not authenticate")


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
    user_object = json.loads(r.content)
    if not user_object['ok']:
        raise Exception(
            "get_user_timezone() failed: " + user_object['error'])
    tz_offset = user_object['user']['tz_offset']
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


def get_scheduled_messages(channel_id, token):
    r = requests.post(
        url="https://slack.com/api/chat.scheduledMessages.list",
        data={
            'channel': channel_id
        },
        headers={
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': "Bearer " + token
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        raise Exception("requests.post failed")
    messages_object = json.loads(r.content)
    if not messages_object['ok']:
        raise Exception(
            "get_scheduled_messages() failed: " + messages_object['error'])
    scheduled_messages = messages_object['scheduled_messages']
    scheduled_messages.sort(key=lambda message_info: message_info['post_at'])
    return scheduled_messages


def list_scheduled_messages(params):
    channel_id = params['channel_id'][0]
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    response_url = params['response_url'][0]
    
    try:
        token = get_user_auth_token(user_id)
    except UserAuthenticateError:
        post_and_print_info_and_confirm_success(
            response_url,
            "You haven't authenticated DelaySay yet."
            "\nPlease grant DelaySay permission to schedule your messages:"
            "\ndelaysay.com/add/?team=" + team_id)
        return
    
    scheduled_messages = get_scheduled_messages(channel_id, token)
    if scheduled_messages:
        res = f"Here are the messages you have scheduled:"
        for i, message_info in enumerate(scheduled_messages):
            print(message_info)
            timestamp = message_info['post_at']
            res += (
               f"\n    " + str(i + 1) + ") <!date^" + str(timestamp)
               + "^{time_secs} on {date_long}|"
               + datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
               + " UTC>")
        res += "\nTo cancel the first message, reply with `/delay delete 1`."
    else:
        res = "Hm... You have no messages scheduled in this channel."
    post_and_print_info_and_confirm_success(response_url, res)


def validate_index_against_scheduled_messages(i, ids, command_text):
    if not ids:
        return "You have no scheduled messages in this channel."
    if i == -1:
        command_phrase = command_text.rsplit(maxsplit=1)[0].rstrip() + " 1"
        return (
            f"Message 0 does not exist. To cancel your first message, type:"
            f"\n        `/delay {command_phrase}`"
            "\nTo list the scheduled messages, reply with `/delay list`.")
    if i >= len(ids):
        return (
            f"Message {i + 1} does not exist."
            "\nTo list the scheduled messages, reply with `/delay list`.")
    return ""


def delete_scheduled_message(params):
    channel_id = params['channel_id'][0]
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    response_url = params['response_url'][0]
    command_text = params['text'][0]
    
    try:
        token = get_user_auth_token(user_id)
    except UserAuthenticateError:
        post_and_print_info_and_confirm_success(
            response_url,
            "You haven't authenticated DelaySay yet."
            "\nPlease grant DelaySay permission to schedule your messages:"
            "\ndelaysay.com/add/?team=" + team_id)
        return
    
    scheduled_messages = get_scheduled_messages(channel_id, token)
    ids = [message_info['id'] for message_info in scheduled_messages]
    command_text_only_numbers = re.compile('[^0-9]').sub('', command_text)
    
    # The array `ids` use 0-based indexing, but the user uses 1-based.
    i = int(command_text_only_numbers) - 1
    
    res = validate_index_against_scheduled_messages(i, ids, command_text)
    if res:
        post_and_print_info_and_confirm_success(response_url, res)
        return
    
    slack_client = slack.WebClient(token=token)
    
    try:
        slack_client.chat_deleteScheduledMessage(
            channel=channel_id,
            scheduled_message_id=ids[i]
        )
        res = f"I successfully cancelled message {command_text_only_numbers}."
    except slack.errors.SlackApiError as err:
        if err.response['error'] == "invalid_scheduled_message_id":
            res = (
                f"I cannot cancel message {command_text_only_numbers};"
                " it already sent or will send within 60 seconds.")
        else:
            raise
    except:
        raise
    
    post_and_print_info_and_confirm_success(response_url, res)


def build_response(res):
    return {
        'statusCode': "200",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
        }
    }


def build_help_response(params, user_asked_for_help=True):
    user_id = params['user_id'][0]
    examples = [
        "2 min say It's been :two: minutes.",
        "1 hour say Hi, all! :wave:",
        "9am PST say Good morning! :sunny:",
        "12 noon say It's time for lunch :yum:",
        "September 13, say It's International Chocolate Day! :chocolate_bar:",
        "January 1, 2020, 12am EST, say Happy New Year! :tada:"
    ]
    two_examples = sample(examples, 2)
    if user_asked_for_help:
      res = f"Hi, <@{user_id}>! Open your favorite channel and type a command:"
    else:
      res = "Here is the command format:"
    res += (
        f"\n        `/delay [time] say [message]`"
        f"\n        `/delay {two_examples[0]}`"
        f"\n        `/delay {two_examples[1]}`"
        "\nI will send the message from your username at the specified date"
        " and time, up to 120 days in the future."
        "\nTo see your scheduled messages in this channel or cancel the next"
        " scheduled message, type:"
        "\n        `/delay list`        or        `/delay delete 1`")
    return build_response(res)


def parse_and_schedule(params):
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    channel_id = params['channel_id'][0]
    command_text = params['text'][0]
    response_url = params['response_url'][0]
    
    try:
        token = get_user_auth_token(user_id)
    except UserAuthenticateError:
        post_and_print_info_and_confirm_success(
            response_url,
            "You haven't authenticated DelaySay yet."
            "\nPlease grant DelaySay permission to schedule your messages:"
            "\ndelaysay.com/add/?team=" + team_id)
        return
    
    user_tz = get_user_timezone(user_id, token)
    
    request_unix_timestamp = params['request_timestamp']
    
    try:
        parser = SlashCommandParser(
            command_text,
            datetime.fromtimestamp(request_unix_timestamp, tz=user_tz))
    except CommandParseError as err:
        post_and_print_info_and_confirm_success(
            response_url,
            f'Sorry, I don\'t understand the command "{err.command_text}".\n'
            + build_help_response(params, user_asked_for_help=False)['body'])
        return
    except TimeParseError as err:
        post_and_print_info_and_confirm_success(
            response_url,
            f'Sorry, I don\'t understand the time "{err.time_text}".')
        return
    
    date = parser.get_date_string_for_slack()
    time = parser.get_time_string_for_slack()
    unix_timestamp = datetime.timestamp(parser.get_time())
    message = parser.get_message()
    
    slack_client = slack.WebClient(token=token)
    try:
        slack_client.chat_scheduleMessage(
            channel=channel_id,
            post_at=unix_timestamp,
            text=message
        )
    except slack.errors.SlackApiError as err:
        if err.response['error'] == "time_in_past":
            if unix_timestamp < request_unix_timestamp:
                apology = "Sorry, I can\'t schedule a message in the past."
            else:
                apology = (
                    "Sorry, I can\'t schedule in the extremely near future.")
            post_and_print_info_and_confirm_success(response_url, apology)
            return
        elif err.response['error'] == "time_too_far":
            post_and_print_info_and_confirm_success(
                response_url,
                "Sorry, I can\'t schedule more than 120 days in the future.")
            return
        elif err.response['error'] == "time_too_far":
            post_and_print_info_and_confirm_success(
                response_url,
                "Sorry, your message is too long:"
                f'\n"{message}"')
            return
        else:
            raise
    
    post_and_print_info_and_confirm_success(
        response_url,
        f'At {time} on {date}, I will post on your behalf: "{message}"'
    )


def respond_before_timeout(event, context):
    # Don't print the event or params, because they have secrets.
    # Or print only the keys.
    params = parse_qs(event['body'])
    user_id = params['user_id'][0]
    command = params['command'][0]
    command_text = params.get('text', [""])[0]
    
    command_text_only_letters = re.compile('[^a-zA-Z]').sub('', command_text)
    if command_text_only_letters in ["help", ""]:
        return build_help_response(params)
    if command_text_only_letters == "list":
        params['currentFunctionOfFunction'] = "list"
    elif command_text_only_letters in ["delete", "cancel", "remove"]:
        params['currentFunctionOfFunction'] = "delete"
    else:
        params['currentFunctionOfFunction'] = "parse/schedule"
    
    params['request_timestamp'] = (
        int(event['multiValueHeaders']['X-Slack-Request-Timestamp'][0]))
    client = boto3.client('lambda')
    client.invoke(
        ClientContext="DelaySay handler",
        FunctionName=context.function_name,
        InvocationType="Event",
        Payload=json.dumps(params)
    )
    
    return build_response(
        f"Hi, <@{user_id}>! Give me a moment to parse your request:"
        f"\n`{command} {command_text}`"
    )


def lambda_handler(event, context):
    function = event.get("currentFunctionOfFunction")
    if function == "parse/schedule":
        print("~~~   PARSER / SCHEDULER   ~~~")
        return parse_and_schedule(event)
    elif function == "list":
        print("~~~   LISTER OF SCHEDULED MESSAGES   ~~~")
        return list_scheduled_messages(event)
    elif function == "delete":
        print("~~~   DELETER OF SCHEDULED MESSAGE   ~~~")
        return delete_scheduled_message(event)
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
        res = (
            "If the error persists, try contacting my developers at"
            " team@delaysay.com.")
        if event.get("currentFunctionOfFunction") and "response_url" in event:
            response_url = event['response_url'][0]
            res = (
                "Sorry, there was an error. Please try again later or rephrase"
                " your command. ") + res
            post_and_print_info_and_confirm_success(response_url, res)
        else:
            res = "Hi, there! Sorry, I'm confused right now. " + res
            return build_response(res)
