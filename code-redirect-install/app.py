import traceback
import os

# This is the Lambda function that creates a 302 redirect to the Slack
# installation OAuth URL; this is for the Slack App Directory entry
# and does not need to be used anywhere else.

SLACK_OAUTH_URL = os.environ['SLACK_OAUTH_URL']


def build_response(res, url):
    return {
        'statusCode': "302",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
            'Location': url
        }
    }


def lambda_handler(event, context):
    url = SLACK_OAUTH_URL
    query_string_parameters = event['queryStringParameters']
    if query_string_parameters:
        team_id = query_string_parameters.get("team")
        if team_id:
          url += "&team=" + team_id
    # JavaScript version from .html page:
    # (eventually convert to Python for Google Analytics tracking)
    # gtag('event', "redirect_to_slack", {
    #   'event_category': "installation",
    #   'event_label': "Team ID: " + (team || "N/A")
    # });
    return build_response("success", url)


def lambda_handler_with_catch_all(event, context):
    try:
        return lambda_handler(event, context)
    except Exception as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        print(traceback.format_exc().replace('\n', '\r'))
        return build_response("error", err)
