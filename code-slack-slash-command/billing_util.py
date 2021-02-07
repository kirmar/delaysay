import os
from uuid import uuid4
from User import User
from BillingToken import BillingToken
from datetime import datetime, timedelta

slash = os.environ['SLASH_COMMAND']
api_domain = os.environ['SLASH_COMMAND_LINKS_DOMAIN']

# When a user generates a billing URL, let them use it for this long.
BILLING_TOKEN_PERIOD = timedelta(hours=1)


def parse_option_and_user(command_text):
    try:
        command, option, user_info = command_text.split()
    except ValueError:
        try:
            command, option = command_text.split()
        except:
            command = command_text
            option = None
        user_info = None
    
    if command not in ["billing", "pay", "subscribe"]:
        option = None
    if option not in ["authorize", "remove"]:
        option = None
        user_id = None
        user = None
    elif user_info == None:
        user_id = None
        user = None
    else:
        # Format: <@W123|username_like_string>
        # According to: https://api.slack.com/changelog/2017-09-the-one-about-usernames
        user_id = user_info.lstrip("<@").split("|")[0]
        user = User(user_id)
        if not user.is_in_dynamodb():
            user = None
    return (option, user_id, user)


def write_message_and_add_or_remove_billing_role(option, user, user_id,
                                                 other_user, other_user_id,
                                                 billing_info):
    assert option in ["authorize", "remove"]
    if not user.is_slack_admin():
        res = (
            "Because you're not an admin in this Slack workspace, you"
            f" cannot control which users manage {billing_info}."
            "\nPlease ask a *workspace admin* to try instead."
        )
    elif option == "authorize" and not other_user_id:
        res = (
            "Please @mention a specific user to allow them to manage"
            f" {billing_info}."
        )
    elif option == "remove" and not other_user_id:
        res = (
            "Please @mention a specific user to remove their ability to manage"
            f" {billing_info}."
        )
    elif option and not other_user:
        res = (
            f"<@{other_user_id}> (member ID: `{other_user_id}`) is not an"
            " authorized DelaySay user."
        )
        # TODO: Maybe mention if they're even a Slack user.
    elif option and user == other_user:
        res = (
            "You are an admin on this workspace, so you are"
            f" automatically authorized to manage {billing_info}."
        )
        if option == "remove":
            res += "\nYou cannot remove your own access."
    elif option == "authorize":
        if other_user.can_manage_billing():
            res = (
                f"<@{other_user_id}> is already authorized to manage"
                f" {billing_info}, so you're all set."
            )
            if not other_user.is_slack_admin():
                res += (
                    "\nYou can remove their access by typing:"
                    f"\n        `{slash} billing remove <@{other_user_id}>`"
                )
        else:
            new_role = other_user.approve_to_manage_billing()
            assert new_role == "approved"
            res = (
                f"<@{other_user_id}> is now authorized to manage"
                f" {billing_info}."
                "\nYou can remove their access by typing:"
                f"\n        `{slash} billing remove <@{other_user_id}>`"
            )
    elif option == "remove":
        if other_user.is_slack_admin():
            res = (
                f"<@{other_user_id}> is an admin on this workspace, like"
                " you, so they are automatically authorized to manage"
                f" {billing_info}."
                "\nYou cannot remove their access."
            )
        elif not other_user.can_manage_billing():
            res = (
                f"<@{other_user_id}> is not currently authorized to manage"
                f" {billing_info}, so you're all set."
                "\nIf you want, you can authorize them by typing:"
                f"\n        `{slash} billing authorize <@{other_user_id}>`"
            )
        else:
            new_role = other_user.disapprove_to_manage_billing()
            assert new_role == "no approval"
            res = (
                f"Thanks! <@{other_user_id}> is no longer authorized to"
                f" manage {billing_info}."
                "\nIf you want, you can authorize them again by typing:"
                f"\n        `{slash} billing authorize <@{other_user_id}>`"
            )
    return res


def generate_billing_url(user_id, team_id, team_name):
    billing_token = BillingToken(token=uuid4().hex)
    billing_token.add_to_dynamodb(
        create_time=datetime.utcnow(),
        expiration_period=BILLING_TOKEN_PERIOD,
        team_id=team_id,
        team_name=team_name,
        user_id=user_id)
    url = f"{api_domain}/billing/?token={billing_token}"
    return url


def write_billing_portal_message(user_id, team_id, team_name, response_url):
    url = generate_billing_url(user_id, team_id, team_name)
    res = (
        "Here's your Stripe customer portal:"
        f"\n{url}"
        "\nIn your billing portal, you can add credit cards, view past"
        " invoices, and manage your DelaySay subscription."
    )
    return res
