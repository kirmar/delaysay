import boto3
import stripe
import time
import os
from datetime import datetime

ssm = boto3.client('ssm')

stripe_api_key_parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_API_KEY_SSM_NAME'],
    WithDecryption=True
)
stripe.api_key = stripe_api_key_parameter['Parameter']['Value']

stripe_test_api_key_parameter = ssm.get_parameter(
    # A slash is needed because the Stripe signing secret parameter
    # in template.yaml is used for the IAM permission (slash forbidden,
    # otherwise the permission will have two slashes in a row and the
    # function won't work) and for accessing the SSM parameter here
    # (slash needed).
    Name="/" + os.environ['STRIPE_TESTING_API_KEY_SSM_NAME'],
    WithDecryption=True
)
TEST_MODE_API_KEY = stripe_test_api_key_parameter['Parameter']['Value']


class StripeSubscription:
    
    def __init__(self, id):
        assert isinstance(id, str)
        self.id = id
        self.last_updated = 0
        self._refresh()
    
    def _refresh(self):
        if time.time() - self.last_updated < 2:
            return
        self.last_updated = time.time()
        try:
            subscription = stripe.Subscription.retrieve(self.id)
        except stripe.error.InvalidRequestError:
            subscription = stripe.Subscription.retrieve(
                self.id, api_key=TEST_MODE_API_KEY)
        self.payment_status = subscription['status']
        unix_timestamp = subscription['current_period_end']
        self.next_expiration = datetime.utcfromtimestamp(unix_timestamp)
        self.plan_name = subscription['plan']['nickname']
    
    def is_current(self):
        self._refresh()
        return self.payment_status == "active"
    
    def get_expiration(self):
        self._refresh()
        return self.next_expiration
    
    def get_plan_nickname(self):
        self._refresh()
        return self.plan_name
