from boto3 import client as boto3_client
from os import environ as os_environ
from hmac import new as hmac_new
from hashlib import sha256 as hashlib_sha256
from time import time

ssm = boto3_client('ssm')
slack_signing_secret_parameter = ssm.get_parameter(
    Name=os_environ['SLACK_SIGNING_SECRET_SSM_NAME'],
    WithDecryption=True
)
SLACK_SIGNING_SECRET = slack_signing_secret_parameter['Parameter']['Value']

# When verifying the Slack signing secret:
# If the timestamp is this old, reject the request.
TIME_TOLERANCE_IN_SECONDS = 5 * 60


def compute_expected_signature(basestring):
    hash = hmac_new(
        key=SLACK_SIGNING_SECRET.encode(),
        msg=basestring.encode(),
        digestmod=hashlib_sha256)
    expected_signature = "v0=" + hash.hexdigest()
    return expected_signature


def verify_slack_signature(request_timestamp, received_signature,
                           request_body):
    # https://api.slack.com/docs/verifying-requests-from-slack
    basestring = "v0:" + request_timestamp + ":" + str(request_body)
    expected_signature = compute_expected_signature(basestring)
    if received_signature != expected_signature:
        # Instead of "received_signature == expected_signature", Slack's
        # docs say "hmac.compare(received_signature, expected_signature)".
        # Which is better?
        raise SlackSignaturesDoNotMatchError("Slack signatures do not match")
    current_timestamp = time()
    if float(current_timestamp) - float(request_timestamp) > TIME_TOLERANCE_IN_SECONDS:
        raise SlackSignatureTimeToleranceExceededError(
            "Tolerance for timestamp difference was exceeded"
            "\ncurrent_timestamp: " + str(current_timestamp) +
            "\nrequest_timestamp: " + str(request_timestamp) +
            "\nTIME_TOLERANCE_IN_SECONDS: " + str(TIME_TOLERANCE_IN_SECONDS))
