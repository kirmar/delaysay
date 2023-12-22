'''
Code included from:
https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/lambda_function.py
'''

import json
import traceback
import boto3
import requests
import slack
import re
import os
from urllib.parse import parse_qs
from datetime import datetime, timedelta
from random import sample

from User import User
from Team import Team
from SlashCommandParser import SlashCommandParser
from DelaySayExceptions import (
    SlackSignaturesDoNotMatchError, SlackSignatureTimeToleranceExceededError,
    UserAuthorizeError, CommandParseError, TimeParseError, AllStripeSubscriptionsInvalid)

from verify_slack_signature import verify_slack_signature
from slack_response_util import (
    post_and_print_info_and_confirm_success, build_response)
from billing_util import (
    parse_option_and_user, write_message_and_add_or_remove_billing_role,
    write_billing_portal_message, generate_billing_url)
from list_and_delete_util import (
    convert_to_slack_datetime, get_scheduled_messages,
    validate_index_against_scheduled_messages)


lambda_client = boto3.client('lambda')

slash = os.environ['SLASH_COMMAND']
api_domain = os.environ['SLASH_COMMAND_LINKS_DOMAIN']
contact_page = os.environ['CONTACT_PAGE']
support_email = os.environ['SUPPORT_EMAIL']
subscribe_url = os.environ['SUBSCRIBE_URL']


# Let the team try DelaySay without paying.
# Start warning them this long before the trial ends.
TRIAL_WARNING_PERIOD = timedelta(days=2)

# Let the team keep using DelaySay, but warn them to pay soon.
# Start warning them this long after the payment expires.
# As of 2020-09-21, I only warn them after the Stripe subscription is
# technically expired, because otherwise they may be asked to pay extra
# when their subscription is already about to automatically charge them.
SUBSCRIPTION_WARNING_PERIOD = timedelta(days=1)

# Let the team keep using DelaySay, but warn them to pay soon.
# Stop access to DelaySay this long after their payment/trial expires.
PAYMENT_GRACE_PERIOD = timedelta(days=2)

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


# Consider 2021 Slack API bug for deleting scheduled messages
# (noticed 2023-12-21 and confirmed by https://stackoverflow.com/a/69843299)
# TODO When Slack fixes this bug, remove these lines and all logic involving them.
MIN_TIME_FOR_DELETION = timedelta(minutes=5)
MIN_TIME_FOR_DELETION_STRING = "5 minutes"


def list_scheduled_messages(params):
    channel_id = params['channel_id'][0]
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    response_url = params['response_url'][0]
    
    user = User(user_id)
    
    try:
        token = user.get_auth_token()
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, I can't check your scheduled texts because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages:"
            f"\n{api_domain}/add/?team=" + team_id)
        return
    
    scheduled_messages = get_scheduled_messages(channel_id, token)
    if scheduled_messages:
        res = f"Here are the messages you have scheduled in this channel with `{slash}`:"
        res += (
            "\nTo cancel the first message"
            f" (if it is sending in over {MIN_TIME_FOR_DELETION_STRING}),"
            f" reply with `{slash} delete 1`.")
        for i, message_info in enumerate(scheduled_messages):
            slack_datetime = convert_to_slack_datetime(timestamp=message_info['post_at'])
            message = message_info['text']
            res += "\n\n"
            res += f"    *{i+1}) {slack_datetime}:*"
            res += f"\n{message}".replace("\n", "\n> ")
    else:
        res = f"You haven't scheduled any messages using `{slash}` in this channel."
    post_and_print_info_and_confirm_success(response_url, res)


def delete_scheduled_message(params):
    channel_id = params['channel_id'][0]
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    response_url = params['response_url'][0]
    command_text = params['text'][0]
    
    user = User(user_id)
    
    try:
        token = user.get_auth_token()
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, your text cannot be canceled because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages:"
            f"\n{api_domain}/add/?team=" + team_id)
        return
    
    scheduled_messages = get_scheduled_messages(channel_id, token)
    if not scheduled_messages:
        res = f"You haven't scheduled any messages using `{slash}` in this channel."
        post_and_print_info_and_confirm_success(response_url, res)
        return
    
    try:
        message_number = int(command_text.split(maxsplit=1)[1])
    except (ValueError, IndexError):
        res = f"To see what messages can be canceled and how, try `{slash} list`."
        post_and_print_info_and_confirm_success(response_url, res)
        return

    # The array `ids` use 0-based indexing, but the user uses 1-based.
    i = message_number - 1
    
    res = validate_index_against_scheduled_messages(i, len(scheduled_messages), command_text)
    if res:
        post_and_print_info_and_confirm_success(response_url, res)
        return
    
    slack_client = slack.WebClient(token=token)
    message_info = scheduled_messages[i]

    if (datetime.utcfromtimestamp(message_info['post_at'])
        <= datetime.utcnow() + MIN_TIME_FOR_DELETION):
        res = (
            f"I can't cancel message {message_number};"
            f" it's scheduled to send within the next {MIN_TIME_FOR_DELETION_STRING}.")
        post_and_print_info_and_confirm_success(response_url, res)
        return
    
    try:
        slack_client.chat_deleteScheduledMessage(
            channel=channel_id,
            scheduled_message_id=message_info['id']
        )
        slack_datetime = convert_to_slack_datetime(timestamp=message_info['post_at'])
        message = message_info['text']
        res = (
            f"I successfully canceled message {message_number},"
            f" which would have been sent {slack_datetime} with the following message:"
            f"\n{message}".replace("\n", "\n> "))
    except slack.errors.SlackApiError as err:
        if err.response['error'] == "invalid_scheduled_message_id":
            res = (
                f"I cannot cancel message {message_number};"
                " it already sent or will send within 60 seconds.")
        else:
            raise
    except:
        raise
    
    post_and_print_info_and_confirm_success(response_url, res)


def respond_to_billing_request(params):
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    team_domain = params['team_domain'][0]
    response_url = params['response_url'][0]
    command_text = params['text'][0]
    
    user = User(user_id)
    team = Team(team_id)
    
    try:
        token = user.get_auth_token()
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, you can't manage your DelaySay billing information"
            " because you haven't authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages:"
            f"\n{api_domain}/add/?team=" + team_id)
        return
    
    billing_info = (
        "your workspace's DelaySay subscription and billing information")
    option, other_user_id, other_user = parse_option_and_user(command_text)
    if option:
        res = write_message_and_add_or_remove_billing_role(
            option, user, user_id, other_user, other_user_id, billing_info)
    elif team.is_trialing():
        if team.get_time_payment_has_been_overdue() > PAYMENT_GRACE_PERIOD:
            res = (
                "Your team's free trial has ended."
                "\nTo continue using DelaySay, *please subscribe here:*"
                f"\n{subscribe_url}/?team={team_id}"
                "\nIf you have any questions, please reach out at"
                f" {contact_page} or {support_email}"
            )
        else:
            res = (
                "Your team is currently on a *free trial* with full access"
                " to all DelaySay features."
                "\nIf you're interested in starting your DelaySay subscription"
                " early before your trial ends, please subscribe here:"
                f"\n{subscribe_url}/?team={team_id}"
                "\nAfter you subscribe, check back here to manage"
                f" {billing_info}."
                # TODO: Add the trial expiration date
            )
    elif team.never_expires():
        res = (
            "Congrats! Your team currently has free access to DelaySay."
            "\nIf you subscribe in the future, check back here to manage"
            f" {billing_info}."
        )
    elif not user.can_manage_billing():
        res = (
            f"You're not authorized to manage {billing_info}."
            "\nPlease ask a *workspace admin* to try instead."
            "\nAn admin can also decide to give you access by typing this:"
            f"\n        `{slash} billing authorize <@{user_id}>`"
        )
    elif False:
        # TODO: Implement a response for when I manually input a payment
        # expiration date, but the team has no Stripe subscription yet.
        pass
    else:
        res = write_billing_portal_message(
            user_id, team_id, team_domain, response_url)
    
    post_and_print_info_and_confirm_success(response_url, res)


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


def parse_and_schedule(params):
    user_id = params['user_id'][0]
    team_id = params['team_id'][0]
    team_domain = params['team_domain'][0]
    channel_id = params['channel_id'][0]
    command_text = params['text'][0]
    response_url = params['response_url'][0]
    
    user = User(user_id)
    team = Team(team_id)
    
    try:
        token = user.get_auth_token()
    except UserAuthorizeError:
        post_and_print_info_and_confirm_success(
            response_url,
            "Sorry, your text cannot be sent because you haven't"
            " authorized DelaySay yet."
            "\n*Please grant DelaySay permission* to schedule your messages,"
            " then try again:"
            f"\n{api_domain}/add/?team=" + team_id +
            "\nIf you have any questions, please reach out at"
            f" {contact_page} or {support_email}")
        return
    
    if team.is_trialing():
        if team.get_time_payment_has_been_overdue() > PAYMENT_GRACE_PERIOD:
            payment_status = "red trial"
        elif team.get_time_till_payment_is_due() < TRIAL_WARNING_PERIOD:
            payment_status = "yellow trial"
        else:
            payment_status = "green"
    else:
        if team.get_time_payment_has_been_overdue() > PAYMENT_GRACE_PERIOD:
            payment_status = "red"
        elif (team.get_time_payment_has_been_overdue()
              > SUBSCRIPTION_WARNING_PERIOD):
            payment_status = "yellow"
        else:
            payment_status = "green"
    
    subscribe_url_with_team_id = f"{subscribe_url}/?team={team_id}"
    
    if payment_status.startswith("red"):
        text = ("\nWe hope you've enjoyed DelaySay! Your *message cannot be"
                " sent* because your workspace's")
        if payment_status == "red trial":
            text += (
                " free trial has ended."
                "\nTo continue using DelaySay, *please subscribe here:*"
                "\n" + subscribe_url_with_team_id +
                "\nIf you have any questions, please reach out at"
                f" {contact_page} or {support_email}"
            )
        else:
            text += " subscription has expired or the last payment failed."
            # TODO: As of 2021-02-06, if the team's subscription was
            # cancelled (not failed), the Stripe customer portal will
            # show payment information but no current plan.
            # And it will not have a way to add a plan.
            # So don't offer to send them to the billing portal.
            # Just have them make a new subscription or contact us.
            if user.can_manage_billing():
                url = generate_billing_url(user_id, team_id, team_domain)
                text += (
                    "\n\nTo see why, please *view your Stripe customer"
                    " portal*:"
                    f"\n{url}"
                )
            else:
                text += (
                    "\n\nTo see why, an admin in your Slack workspace can type"
                    " this to *view your Stripe customer portal*:"
                    f"\n        `{slash} billing`"
                )
            text += (
                "\nIn your billing portal, you can add credit cards, view past"
                " invoices, and manage your DelaySay subscription."
                "\n\nOr if you prefer, you can start a new subscription:"
                "\n" + subscribe_url_with_team_id +
                "\n\nIf you have any questions or concerns, we'd be happy to"
                f" chat with you at {contact_page} or {support_email}"
            )
        
        post_and_print_info_and_confirm_success(response_url, text)
        return
    # fi payment_status.startswith("red")
    
    request_unix_timestamp = params['request_timestamp']
    
    user_tz = user.get_timezone()
    try:
        parser = SlashCommandParser(
            command_text,
            datetime.fromtimestamp(request_unix_timestamp, tz=user_tz))
    except CommandParseError as err:
        post_and_print_info_and_confirm_success(
            response_url,
            "*Sorry, I don't understand. Please try again.*\n"
            + build_help_response(params, user_asked_for_help=False)['body'])
        return
    except TimeParseError as err:
        post_and_print_info_and_confirm_success(
            response_url,
            f'I don\'t understand the time "{err.time_text}".'
            f" *Please rephrase the time* or try `{slash} help`.")
        return
    
    date = parser.get_date_string_for_slack()
    time = parser.get_time_string_for_slack()
    unix_timestamp = datetime.timestamp(parser.get_time())
    message = parser.get_message()

    if not message:
        error_text = "I can't schedule an empty message."
        post_and_print_info_and_confirm_success(response_url, error_text)
        return
    
    slack_client = slack.WebClient(token=token)
    try:
        slack_client.chat_scheduleMessage(
            channel=channel_id,
            post_at=unix_timestamp,
            text=message
        )
    except slack.errors.SlackApiError as err:
        error_code = err.response['error']
        if error_code == "time_in_past":
            if unix_timestamp < request_unix_timestamp:
                error_text = "Slack can't schedule a message in the past."
            else:
                error_text = "Slack can't schedule in the extremely near future."
        elif error_code == "time_too_far":
            error_text = "Slack can't schedule too far into the future, typically 120 days."
        elif error_code == "msg_too_long":
            error_text = (
                f"Slack can't schedule a message if it's too long; yours is {len(message)} characters.")
        elif error_code == "restricted_too_many":
            error_text = "Slack can't schedule too many messages too close together."
        else:
            raise
        post_and_print_info_and_confirm_success(response_url, error_text)
        return
    
    text = (
        f'At {time} on {date}, I will post on your behalf:'
        f'\n{message}'.replace("\n", "\n> "))
    if payment_status.startswith("yellow"):
        text += "\n\nWe hope you're enjoying DelaySay! Your workspace's"
        if payment_status == "yellow trial":
            text += " free trial is almost over."
        elif payment_status == "yellow":
            text += " subscription is expiring."
        text += ("\nTo continue using DelaySay, *please subscribe here:*"
                 "\n" + subscribe_url_with_team_id +
                 "\nIf you have any questions, please reach out at"
                 f" {contact_page} or {support_email}")
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
        FunctionName=context.function_name,
        InvocationType="Event",
        Payload=json.dumps(params)
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
    elif function == "billing":
        print("~~~   BILLING / STRIPE CUSTOMER PORTAL   ~~~")
        return respond_to_billing_request(event)
    elif 'ssl_check' in event and event['ssl_check'] == 1:
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
        print(traceback.format_exc().replace('\n', '\r'))
        return build_response(
            "Hi, there! There's been an issue, error 403-A."
            + support_message)
    except SlackSignatureTimeToleranceExceededError:
        print(traceback.format_exc().replace('\n', '\r'))
        return build_response(
            "Hi, there! There's been an issue, error 403-B."
            + support_message)
    except AllStripeSubscriptionsInvalid as err:
        support_message = (
            "\nIf you have any questions, feel free to reach out at"
            f" {contact_page} or {support_email}")
        print(traceback.format_exc().replace('\n', '\r'))
        if err.team_id:
            support_message = (
                "\nTo continue using DelaySay, *please re-subscribe here:*"
                f"\n{subscribe_url}/?team={err.team_id}"
                + support_message)
        if event.get("currentFunctionOfFunction") and "response_url" in event:
            response_url = event['response_url'][0]
            res = (
                "Sorry, you don't have a valid subscription."
                + support_message)
            post_and_print_info_and_confirm_success(response_url, res)
        else:
            return build_response(
                "Hi, there! Sorry, you don't have a valid subscription."
                + support_message)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the message parsed by SlashCommandParser.
        print(traceback.format_exc().replace('\n', '\r'))
        if event.get("currentFunctionOfFunction") and "response_url" in event:
            response_url = event['response_url'][0]
            res = (
                "Sorry, there was an error. Please try again later or rephrase"
                " your command. ") + support_message
            post_and_print_info_and_confirm_success(response_url, res)
        else:
            res = "Hi, there! Sorry, I'm confused right now. " + support_message
            return build_response(res)
