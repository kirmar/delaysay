import requests
import json


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
