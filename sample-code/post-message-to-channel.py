import os
import slack
import boto3

slack_token_name = os.environ["SLACK_API_TOKEN_NAME"]
slack_channel_id = os.environ["SLACK_CHANNEL_ID"]

ssm_client = boto3.client('ssm')
parameter = ssm_client.get_parameter(
    Name=slack_token_name,
    WithDecryption=True
)
slack_token = parameter['Parameter']['Value']

slack_client = slack.WebClient(token=slack_token)

slack_client.chat_postMessage(
    channel=slack_channel_id,
    text="Hello, world! :tada:"
)

# # Why don't link_names=True and username="DelaySay" and
# # icon_emoji=":robot_face:" work??
# slack_client.chat_postMessage(
#     channel=slack_channel_id,
#     link_names=1,
#     text=f"Hello, @{slack_channel_id}! :tada:",
#     username='DelaySay',
#     icon_emoji=':robot_face:'
# )
