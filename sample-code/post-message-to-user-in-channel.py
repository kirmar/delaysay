import os
import slack
import boto3

slack_token_name = os.environ["SLACK_API_TOKEN_NAME"]
slack_channel_id = os.environ["SLACK_CHANNEL_ID"]
recipient_name = os.environ["RECIPIENT"]
recipient_id = os.environ["RECIPIENT_ID"]

ssm_client = boto3.client('ssm')
parameter = ssm_client.get_parameter(
    Name=slack_token_name,
    WithDecryption=True
    )
slack_token = parameter['Parameter']['Value']

slack_client = slack.WebClient(token=slack_token)

slack_client.chat_postEphemeral(
    channel=slack_channel_id,
    text=f"Hello, {recipient_name}! :tada: This is a private message sent"
         " through the Slack SDK for Python",
    user=recipient_id
    )
