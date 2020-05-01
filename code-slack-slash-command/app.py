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
import hashlib
import hmac
import time
import re
import aws_encryption_sdk
from urllib.parse import parse_qs
from StripeSubscription import StripeSubscription
from SlashCommandParser import SlashCommandParser
from DelaySayExceptions import (
    SlackSignaturesDoNotMatchError, SlackSignatureTimeToleranceExceededError,
    UserAuthorizeError, CommandParseError, TimeParseError)
from datetime import datetime, timezone, timedelta
from random import sample

kms_key_provider = aws_encryption_sdk.KMSMasterKeyProvider(key_ids=[
    os.environ['KMS_MASTER_KEY_ARN']
])

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])

ssm = boto3.client('ssm')

slack_signing_secret_parameter = ssm.get_parameter(
    # A slash is needed because the Slack signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['SLACK_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
SLACK_SIGNING_SECRET = slack_signing_secret_parameter['Parameter']['Value']


# When verifying the Slack signing secret:
# If the timestamp is this old, reject the request.
TIME_TOLERANCE_IN_SECONDS = 5 * 60


# Let the team try DelaySay without paying.
# Start warning them this long before the trial ends.
TRIAL_WARNING_PERIOD = timedelta(days=2)

# Let the team keep using DelaySay, but warn them to pay soon.
# Start warning them this long before the payment expires.
# As of 2020-04-30, timedelta(days=0) means they won't be warned at all.
SUBSCRIPTION_WARNING_PERIOD = timedelta(days=0)

# Let the team keep using DelaySay, but warn them to pay soon.
# Stop access to DelaySay this long after their payment/trial expires.
PAYMENT_GRACE_PERIOD = timedelta(days=1)

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def compute_expected_signature(basestring):
    hash = hmac.new(
        key=SLACK_SIGNING_SECRET.encode(),
        msg=basestring.encode(),
        digestmod=hashlib.sha256)
    expected_signature = "v0=" + hash.hexdigest()
    return expected_signature


def verify_slack_signature(request_timestamp, received_signature, request_body):
    # https://api.slack.com/docs/verifying-requests-from-slack
    basestring = "v0:" + request_timestamp + ":" + str(request_body)
    expected_signature = compute_expected_signature(basestring)
    if received_signature != expected_signature:
        # Instead of "received_signature == expected_signature", Slack's
        # docs say "hmac.compare(received_signature, expected_signature)".
        # Which is better?
        raise SlackSignaturesDoNotMatchError("Slack signatures do not match")
    current_timestamp = time.time()
    if float(current_timestamp) - float(request_timestamp) > TIME_TOLERANCE_IN_SECONDS:
        raise SlackSignatureTimeToleranceExceededError(
            "Tolerance for timestamp difference was exceeded"
            "\ncurrent_timestamp: " + str(current_timestamp) +
            "\nrequest_timestamp: " + str(request_timestamp) +
            "\nTIME_TOLERANCE_IN_SECONDS: " + str(TIME_TOLERANCE_IN_SECONDS))


def decrypt_oauth_token(encrypted_token):
    token_as_bytes, decryptor_header = aws_encryption_sdk.decrypt(
        source=encrypted_token,
        key_provider=kms_key_provider
    )
    token = token_as_bytes.decode()
    return token


def get_user_auth_token(user_id):
    response = table.get_item(
        Key={
            'PK': "USER#" + user_id,
            'SK': "user"
        }
    )
    try:
        encrypted_token_as_boto3_binary = response['Item']['token']
    except KeyError:
        raise UserAuthorizeError("User did not authorize")
    encrypted_token_as_bytes = encrypted_token_as_boto3_binary.value
    return decrypt_oauth_token(encrypted_token_as_bytes)


def get_payment_expiration_from_dynamodb(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
            }
    )
    expiration_string = response['Item']['payment_expiration']
    try:
        expiration = datetime.strptime(expiration_string, DATETIME_FORMAT)
        return expiration
    except:
        return expiration_string


def get_subscription_id_from_dynamodb(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        }
    )
    subscription_id = response['Item'].get('stripe_subscription_id')
    return subscription_id


def get_payment_plan_nickname_from_dynamodb(team_id):
    assert team_id
    response = table.get_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
            }
    )
    payment_plan = response['Item']['payment_plan']
    return payment_plan


def check_payment_status(payment_expiration, trial=False):
    # The team's trial has ended, so check if payment is current.
    if payment_expiration == "never":
        return "green"
    now = datetime.utcnow()
    time_till_expiration = payment_expiration - now
    time_since_expiration = now - payment_expiration
    if time_till_expiration > (TRIAL_WARNING_PERIOD if trial
                               else SUBSCRIPTION_WARNING_PERIOD):
        return "green"
    elif time_since_expiration <= PAYMENT_GRACE_PERIOD:
            return "yellow" + (" trial" if trial else "")
    elif time_since_expiration > PAYMENT_GRACE_PERIOD:
        return "red" + (" trial" if trial else "")
    else:
        raise Exception(
            "check_payment_status() failed: " +
            "\npayment_expiration: " + str(payment_expiration) +
            "\ntime_till_expiration: " + str(time_till_expiration) +
            "\ntrial: " + str(trial) +
            "\nTRIAL_WARNING_PERIOD: " + str(TRIAL_WARNING_PERIOD) +
            "\nSUBSCRIPTION_WARNING_PERIOD: " + str(SUBSCRIPTION_WARNING_PERIOD) +
            "\nPAYMENT_GRACE_PERIOD: " + str(PAYMENT_GRACE_PERIOD))


def update_payment_info(team_id, payment_expiration, payment_plan,
                        stripe_subscription_id):
    assert team_id and payment_expiration and payment_plan
    assert stripe_subscription_id
    table.update_item(
        Key={
            'PK': "TEAM#" + team_id,
            'SK': "team"
        },
        UpdateExpression="SET payment_expiration = :val,"
                         " payment_plan = :val2,"
                         " stripe_subscription_id = :val3",
        ExpressionAttributeValues={
            ":val": payment_expiration,
            ":val2": payment_plan,
            ":val3": stripe_subscription_id
        }
    )


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
            "get_user_timezone() failed: " + user_object['error'] +
            "\nFor more information, see here:"
            "\nhttps://api.slack.com/methods/users.info")
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
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, I can't check your scheduled texts because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages:"
            "\ndelaysay.com/add/?team=" + team_id)
        return
    
    scheduled_messages = get_scheduled_messages(channel_id, token)
    if scheduled_messages:
        res = f"Here are the messages you have scheduled:"
        for i, message_info in enumerate(scheduled_messages):
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
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, your text cannot be canceled because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages:"
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
        res = f"I successfully canceled message {command_text_only_numbers}."
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
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, your text cannot be sent because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages,"
            " then try again:"
            "\ndelaysay.com/add/?team=" + team_id)
        return
    
    user_tz = get_user_timezone(user_id, token)
    
    expiration = get_payment_expiration_from_dynamodb(team_id)
    plan_name = get_payment_plan_nickname_from_dynamodb(team_id)
    if plan_name == "trial":
        payment_status = check_payment_status(expiration, trial=True)
    else:
        payment_status = check_payment_status(expiration)
        subscription_id = get_subscription_id_from_dynamodb(team_id)
        subscription = StripeSubscription(subscription_id)
        if (payment_status in ["yellow", "red"] and subscription.is_current()):
            expiration_from_stripe = subscription.get_expiration()
            plan_name_from_stripe = subscription.get_plan_nickname()
            if expiration_from_stripe > expiration:
                # The Stripe subscription was paid recently and
                # the expiration should be updated accordingly.
                expiration = expiration_from_stripe
                expiration_string = expiration.strftime(DATETIME_FORMAT)
                update_payment_info(team_id, expiration_string, plan_name, subscription_id)
            payment_status = check_payment_status(expiration)
    subscribe_url = "delaysay.com/subscribe/?team=" + team_id
    
    if payment_status.startswith("red"):
        text = ("\nWe hope you've enjoyed DelaySay! Your message cannot be"
                " sent because your workspace's")
        if payment_status == "red trial":
            text += " free trial has ended."
        elif payment_status == "red":
            text += " subscription has expired."
        text += ("\nTo continue using DelaySay, *please pay here:*"
                 "\n" + subscribe_url +
                 "\nIf you have any questions, reach us at team@delaysay.com")
        post_and_print_info_and_confirm_success(response_url, text)
        return
    
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
    
    text = f'At {time} on {date}, I will post on your behalf: "{message}"'
    if payment_status.startswith("yellow"):
        text += "\n\nWe hope you're enjoying DelaySay! Your workspace's"
        if payment_status == "yellow trial":
            text += " free trial is almost over."
        elif payment_status == "yellow":
            text += " subscription is expiring."
        text += ("\nTo continue using DelaySay, *please pay here:*"
                 "\n" + subscribe_url +
                 "\nIf you have any questions, reach us at team@delaysay.com")
    post_and_print_info_and_confirm_success(response_url, text)


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
        verify_slack_signature(
            request_timestamp=event['headers']['X-Slack-Request-Timestamp'],
            received_signature=event['headers']['X-Slack-Signature'],
            request_body=event['body'])
        return respond_before_timeout(event, context)


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except SlackSignaturesDoNotMatchError:
        traceback.print_exc()
        return build_response(
            "Hi, there! I can't respond to your request because it has an"
            " invalid Slack signature. It's a security risk.")
    except SlackSignatureTimeToleranceExceededError:
        traceback.print_exc()
        return build_response(
            "Hi, there! I can't respond to your request because it was sent"
            " long ago. It's a security risk.")
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the message parsed by SlashCommandParser.
        traceback.print_exc()
        res = (
            "If the error persists, try contacting us at team@delaysay.com")
        if event.get("currentFunctionOfFunction") and "response_url" in event:
            response_url = event['response_url'][0]
            res = (
                "Sorry, there was an error. Please try again later or rephrase"
                " your command. ") + res
            post_and_print_info_and_confirm_success(response_url, res)
        else:
            res = "Hi, there! Sorry, I'm confused right now. " + res
            return build_response(res)
