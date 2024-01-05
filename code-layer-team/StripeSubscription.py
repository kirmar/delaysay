from boto3 import client as boto3_client
from time import time
from os import environ as os_environ
from datetime import datetime

def setup():
    ssm = boto3_client('ssm')

    stripe_api_key_parameter = ssm.get_parameter(
        Name=os_environ['STRIPE_API_KEY_SSM_NAME'],
        WithDecryption=True
    )
    API_KEY = stripe_api_key_parameter['Parameter']['Value']

    stripe_test_api_key_parameter = ssm.get_parameter(
        Name=os_environ['STRIPE_TESTING_API_KEY_SSM_NAME'],
        WithDecryption=True
    )
    TEST_MODE_API_KEY = stripe_test_api_key_parameter['Parameter']['Value']
    return (API_KEY, TEST_MODE_API_KEY)


class StripeSubscription:

    SETUP_DONE = False
    API_KEY = None
    TEST_MODE_API_KEY = None
    
    def __init__(self, id):
        assert id and isinstance(id, str)
        if not StripeSubscription.SETUP_DONE:
            (StripeSubscription.API_KEY,
             StripeSubscription.TEST_MODE_API_KEY) = setup()
            StripeSubscription.SETUP_DONE = True
        self.id = id
        self.last_updated = 0
        self._refresh()
    
    def _refresh(self):
        if time() - self.last_updated < 2:
            return
        from stripe import (
            Subscription as stripe_Subscription,
            error as stripe_error)
        self.last_updated = time()
        self.mode = "live"
        try:
            subscription = stripe_Subscription.retrieve(
                self.id, api_key=StripeSubscription.API_KEY)
        except stripe_error.InvalidRequestError:
            self.mode = "test"
            subscription = stripe_Subscription.retrieve(
                self.id, api_key=StripeSubscription.TEST_MODE_API_KEY)
        self.payment_status = subscription['status']
        unix_timestamp = subscription['current_period_end']
        self.next_expiration = datetime.utcfromtimestamp(unix_timestamp)
        self.plan_name = subscription['plan']['nickname']
        self.customer_id = subscription['customer']
    
    def is_current(self):
        self._refresh()
        has_not_expired = (datetime.utcnow() < self.next_expiration)
        is_paid = (self.payment_status == "active")
        return has_not_expired and is_paid
    
    def get_expiration(self):
        self._refresh()
        return self.next_expiration
    
    def get_plan_nickname(self):
        self._refresh()
        return self.plan_name
    
    def get_customer_id(self):
        self._refresh()
        return self.customer_id
    
    def is_in_test_mode(self):
        self._refresh()
        return self.mode == "test"
    
    def __gt__(self, other):
        if self.is_current() and not other.is_current():
            # Ignore the canceled/expired subscription (other)
            return True
        elif other.is_current() and not self.is_current():
            # Ignore the canceled/expired subscription (self)
            return False
        else:
            self._refresh()
            return self.next_expiration > other.get_expiration()
