import os
import slack
import boto3
import datetime

slack_token_name = os.environ["SLACK_API_TOKEN_NAME"]
slack_channel_id = os.environ["SLACK_CHANNEL_ID"]

ssm_client = boto3.client('ssm')
parameter = ssm_client.get_parameter(
    Name=slack_token_name,
    WithDecryption=True
)
slack_token = parameter['Parameter']['Value']

slack_client = slack.WebClient(token=slack_token)

today = datetime.date.today().strftime("%Y-%m-%d")

slack_client.chat_postMessage(
    channel=slack_channel_id,
    blocks=[
    	{
    		"type": "section",
    		"text": {
    			"type": "mrkdwn",
    			"text": "Pick a date to send the message."
    		},
    		"accessory": {
    			"type": "datepicker",
    			"initial_date": today,
    			"placeholder": {
    				"type": "plain_text",
    				"text": "Select a date",
    				"emoji": True
    			}
    		}
    	}
    ]
)
