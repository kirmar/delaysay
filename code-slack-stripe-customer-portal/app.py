import boto3
import stripe
import traceback
import os
from BillingToken import BillingToken
from Team import Team
from DelaySayExceptions import BillingTokenInvalidError

# This is the Lambda function that creates a redirect to a specific
# team's billing portal.

BILLING_PORTAL_FAIL_URL = os.environ['BILLING_PORTAL_FAIL_URL']

ssm = boto3.client('ssm')

stripe_api_key_parameter = ssm.get_parameter(
    Name=os.environ['STRIPE_API_KEY_SSM_NAME'],
    WithDecryption=True
)
stripe.api_key = stripe_api_key_parameter['Parameter']['Value']

stripe_test_api_key_parameter = ssm.get_parameter(
    Name=os.environ['STRIPE_TESTING_API_KEY_SSM_NAME'],
    WithDecryption=True
)
TEST_MODE_API_KEY = stripe_test_api_key_parameter['Parameter']['Value']


def build_response(res, url):
    return {
        'statusCode': "302",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
            'Location': url
        }
    }


def redirect_because_invalid_token():
    return build_response("failed", BILLING_PORTAL_FAIL_URL)


def fetch_stripe_subscription(token):
    try:
        billing_token = BillingToken(token)
        if billing_token.has_expired():
            raise BillingTokenInvalidError(
                "Billing token expired: " + str(billing_token))
        team_id = billing_token.get_team_id()
    except BillingTokenInvalidError:
        raise
    
    team = Team(team_id)
    
    if team.is_trialing():
        # This shouldn't happen
        # (should be caught in the slash command;
        # the URL actually shouldn't have generated).
        # But if it does, exit gracefully.
        # Otherwise, the function'll get upset later because
        # the team doesn't have a self.best_subscription.
        raise BillingTokenInvalidError(
            "Team is on free trial: " + str(team_id)
            + "\nBilling token: " + str(billing_token))
        # TODO: Redirect to a pretty page instead
    
    if team.never_expires():
        # This shouldn't happen either, but just in case!
        raise BillingTokenInvalidError(
            "Team's 'payment' never expires: " + str(team_id)
            + "\nBilling token: " + str(billing_token))
        # TODO: Redirect to a pretty page instead
    
    # TODO: Implement a response for when I manually input a payment
    # expiration date, but the team has no Stripe subscription yet.
    
    stripe_subscription = team.get_best_subscription()
    return stripe_subscription


def lambda_handler(event, context):
    query_string_parameters = event['queryStringParameters']
    if query_string_parameters:
        token = query_string_parameters.get("token")
    else:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        print(
            f"Redirecting to {BILLING_PORTAL_FAIL_URL} because:"
            "\rNo query string parameters")
        return redirect_because_invalid_token()
    
    try:
        stripe_subscription = fetch_stripe_subscription(token)
    except BillingTokenInvalidError as err:
        # Maybe remove this, since it could print sensitive information,
        # like the user's OAuth token.
        print(
            f"Redirecting to {BILLING_PORTAL_FAIL_URL} because:"
            f"\r{err}.".replace('\n', '\r'))
        return redirect_because_invalid_token()
    
    customer_id = stripe_subscription.get_customer_id()
    if stripe_subscription.is_in_test_mode():
        stripe.api_key = TEST_MODE_API_KEY
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://delaysay.com/",
        # could also create a thank-you page
        # or return to their Slack workspace:
        # return_url="https://app.slack.com/client/" + team_id,
    )
    url = session.url
    
    # JavaScript version from .html page:
    # (eventually convert to Python for Google Analytics tracking)
    # gtag('event', "redirect_to_slack", {
    #   'event_category': "billing"
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
