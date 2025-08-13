'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

from json import dumps as json_dumps
from traceback import format_exc
from boto3 import client as boto3_client
from re import compile as re_compile
from os import environ as os_environ
from urllib.parse import parse_qs
from random import sample as random_sample

from DelaySayExceptions import (
    SlackSignaturesDoNotMatchError, SlackSignatureTimeToleranceExceededError)

from verify_slack_signature import verify_slack_signature

lambda_client = boto3_client('lambda')

second_responder_function = os_environ['SECOND_RESPONDER_FUNCTION']
slash = os_environ['SLASH_COMMAND']
contact_page = os_environ['CONTACT_PAGE']
support_email = os_environ['SUPPORT_EMAIL']


def build_response(res):
    return {
        'statusCode': "200",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
        }
    }


def build_help_response(params):
    user_id = params['user_id'][0]
    examples = [
        "2 min say It's been :two: minutes.",
        "1 hour say Hi, all! :wave:",
        "9am PST say Good morning! :sunny:",
        "12 noon say It's time for lunch :yum:",
        "September 13, say It's International Chocolate Day! :chocolate_bar:",
        "January 1, 2020, 12am EST, say Happy New Year! :tada:"
    ]
    two_examples = random_sample(examples, 2)
    res = f"Hi, <@{user_id}>! Open your favorite channel and type a command:"
    res += (
        f"\n        `{slash} [time] say [message]`"
        f"\n        `{slash} {two_examples[0]}`"
        f"\n        `{slash} {two_examples[1]}`"
        "\nI will send the message from your username at the specified date"
        " and time, up to 120 days in the future. (Can't schedule messages to"
        " send in the past yet, but we'll consider adding this feature"
        " once time travel is possible!)"
        "\n\nTo see your scheduled messages in this channel or cancel the next"
        " scheduled message, type:"
        f"\n        `{slash} list`        or        `{slash} delete 1`"
        "\n\nIf you're an admin in this Slack workspace, you can view past"
        " invoices, update your payment information, and more in your Stripe"
        " customer portal:"
        f"\n        `{slash} billing`"
        "\nAdmins can also give another user access to your workspace's"
        " billing portal by typing this:"
        f"\n        `{slash} billing authorize @username`"
        f"\n\nQuestions? Please reach out at {contact_page} or {support_email}")
    return build_response(res)


def respond_before_timeout(event, context):
    # Don't print the event or params, because they have secrets.
    # Or print only the keys.
    params = parse_qs(event['body'])
    user_id = params['user_id'][0]
    command = params['command'][0]
    command_text = params.get('text', [""])[0]
    
    command_text_only_letters = re_compile('[^a-zA-Z]').sub('', command_text)
    if command_text_only_letters in ["help", ""]:
        return build_help_response(params)
    if command_text_only_letters == "list":
        params['currentFunctionOfFunction'] = "list"
    elif command_text_only_letters in ["delete", "cancel", "remove"]:
        params['currentFunctionOfFunction'] = "delete"
    elif (command_text_only_letters.startswith("billing")
          or command_text_only_letters.startswith("pay")
          or command_text_only_letters.startswith("subscribe")):
        params['currentFunctionOfFunction'] = "billing"
    else:
        params['currentFunctionOfFunction'] = "parse/schedule"
    
    params['request_timestamp'] = (
        int(event['multiValueHeaders']['X-Slack-Request-Timestamp'][0]))
    lambda_client.invoke(
        ClientContext="DelaySay handler",
        FunctionName=second_responder_function,
        InvocationType="Event",
        Payload=json_dumps(params)
    )
    
    user_command = f"{command} {command_text}"
    if "\n" in user_command:
        user_command = f"```{user_command}```"
    else:
        user_command = f"`{user_command}`"
    return build_response(
        f"Hi, <@{user_id}>! Give me a moment to parse your request:"
        f"\n{user_command}")


def lambda_handler(event, context):
    if 'ssl_check' in event and event['ssl_check'] == 1:
        print("~~~   VERIFICATION OF SSL CERTIFICATE   ~~~")
        verify_slack_signature(
            request_timestamp=event['headers']['X-Slack-Request-Timestamp'],
            received_signature=event['headers']['X-Slack-Signature'],
            request_body=event['body'])
        return build_response("")
    else:
        print("~~~   FIRST RESPONDER BEFORE TIMEOUT   ~~~")
        verify_slack_signature(
            request_timestamp=event['headers']['X-Slack-Request-Timestamp'],
            received_signature=event['headers']['X-Slack-Signature'],
            request_body=event['body'])
        return respond_before_timeout(event, context)


def lambda_handler_with_catch_all(event, context):
    support_message = (
        "\nIf the error persists, feel free to reach out at"
        f" {contact_page} or {support_email}")
    try:
        return lambda_handler(event, context)
    except SlackSignaturesDoNotMatchError:
        print(format_exc().replace('\n', '\r'))
        return build_response(
            "Hi, there! There's been an issue, error 403-A."
            + support_message)
    except SlackSignatureTimeToleranceExceededError:
        print(format_exc().replace('\n', '\r'))
        return build_response(
            "Hi, there! There's been an issue, error 403-B."
            + support_message)
    except Exception:
        # Maybe remove this, since it could print sensitive information,
        # like the message parsed by SlashCommandParser.
        print(format_exc().replace('\n', '\r'))
        res = "Hi, there! Sorry, I'm confused right now. " + support_message
        return build_response(res)
