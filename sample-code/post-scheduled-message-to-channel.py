import os
import slack
import boto3
import time

slack_token_name = os.environ["SLACK_API_TOKEN_NAME"]
slack_channel_id = os.environ["SLACK_CHANNEL_ID"]

ssm_client = boto3.client('ssm')
parameter = ssm_client.get_parameter(
    Name=slack_token_name,
    WithDecryption=True
)
slack_token = parameter['Parameter']['Value']

slack_client = slack.WebClient(token=slack_token)

slack_client.chat_scheduleMessage(
    channel=slack_channel_id,
    post_at=time.time() + 60,
    text="Hello, world! :tada: This is a scheduled message."
)
