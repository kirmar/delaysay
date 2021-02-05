import boto3
import time
import os
from StripeSubscription import StripeSubscription
from datetime import datetime, timedelta

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class Team:
    
    def __init__(self, id):
        assert id and isinstance(id, str)
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])
        self.id = id
        self.last_updated = 0
        self._refresh()
    
    def _get_payment_expiration_as_string(self):
        if self.never_expires():
            payment_expiration_as_string = self.payment_expiration
        elif isinstance(self.payment_expiration, datetime):
            payment_expiration_as_string = (
                self.payment_expiration.strftime(DATETIME_FORMAT))
        else:
            # This shouldn't ever happen, but if it does, I at least
            # want to know what happened.
            payment_expiration_as_string = str(self.payment_expiration)
        return payment_expiration_as_string
    
    def _load_subscriptions(self):
        subscriptions = []
        for id in self.subscription_ids:
            subscription = StripeSubscription(id)
            subscriptions.append(subscription)
        return subscriptions
    
    def _update_payment_info_in_dynamodb(self):
        payment_expiration_as_string = self._get_payment_expiration_as_string()
        self.table.update_item(
            Key={
                'PK': "TEAM#" + self.id,
                'SK': "team"
            },
            UpdateExpression=
                "SET payment_expiration = :val,"
                " payment_plan = :val2",
            ExpressionAttributeValues={
                ":val": payment_expiration_as_string,
                ":val2": self.payment_plan
            }
        )
    
    def _update_payment_info(self):
        # Note as of 2020-05-02: The "best_subscription" is the one that
        # expires latest or, if all others are expired/canceled, the only
        # active subscription.
        if self.never_expires():
            return
        subscriptions = self._load_subscriptions()
        if subscriptions:
            best_subscription = max(subscriptions)
        else:
            # The team is probably in the middle of a trial.
            return
        if not best_subscription.is_current():
            return
        self.payment_expiration = best_subscription.get_expiration()
        self.payment_plan = best_subscription.get_plan_nickname()
        self.best_subscription = best_subscription
        self._update_payment_info_in_dynamodb()
    
    def _refresh(self, force=False, alert_if_not_in_dynamodb=False):
        # Careful with this function!! Some of the functions
        # that call it are called (directly or indirectly)
        # by it, like get_time_payment_has_been_overdue()
        # and also never_expires().
        if not force and time.time() - self.last_updated < 2:
            return
        self.last_updated = time.time()
        response = self.table.get_item(
            Key={
                'PK': "TEAM#" + self.id,
                'SK': "team"
                }
        )
        if 'Item' not in response:
            self.is_in_dynamodb = False
            if alert_if_not_in_dynamodb:
                # 2020-05-04: For some reason, this wasn't called.
                # Is 'Item' in response even when the item doesn't
                # exist in the DynamoDB table?
                raise TeamNotInDynamoDBError("Unauthorized team: " + self.id)
            else:
                return
        self.is_in_dynamodb = True
        date = response['Item']['payment_expiration']
        try:
            self.payment_expiration = datetime.strptime(date, DATETIME_FORMAT)
        except:
            # The expiration is probably "never".
            self.payment_expiration = date
        self.payment_plan = response['Item']['payment_plan']
        self.subscription_ids = response['Item'].get(
            'stripe_subscriptions', [])
        if self.get_time_payment_has_been_overdue() > timedelta(0):
            self._update_payment_info()
    
    def is_trialing(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.payment_plan == "trial"
    
    def never_expires(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        if not isinstance(self.payment_expiration, datetime):
            # The expiration is probably "never".
            return True
        return False
    
    def get_time_till_payment_is_due(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        if self.never_expires():
            return timedelta(weeks=52*100)
        now = datetime.utcnow()
        return self.payment_expiration - now
    
    def get_time_payment_has_been_overdue(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        if self.never_expires():
            return timedelta(0)
        now = datetime.utcnow()
        return now - self.payment_expiration
    
    def add_to_dynamodb(self, team_name, enterprise_id, create_time,
                        trial_expiration):
        self._refresh()
        if self.is_in_dynamodb:
            return
        item = {
            'PK': "TEAM#" + self.id,
            'SK': "team",
            'team_name': team_name,
            'team_id': self.id,
            'enterprise_id': enterprise_id,
            'create_time': create_time.strftime(DATETIME_FORMAT),
            'payment_expiration': trial_expiration.strftime(DATETIME_FORMAT),
            'payment_plan': "trial",
            'stripe_subscriptions': []
        }
        for key in list(item):
            if key == 'stripe_subscriptions':
                continue
            if not item[key]:
                del item[key]
        self.table.put_item(Item=item)
        self._refresh(force=True)
    
    def add_subscription(self, subscription_id):
        # Note as of 2020-05-02: There should only be one subscription
        # for each team, but in the case that there are multiple,
        # I want DynamoDB to keep track for debugging/support purposes.
        self._refresh(alert_if_not_in_dynamodb=True)
        self.subscription_ids.append(subscription_id)
        self._update_payment_info()
        self.table.update_item(
            Key={
                'PK': "TEAM#" + self.id,
                'SK': "team"
            },
            UpdateExpression=
                "SET stripe_subscriptions"
                " = list_append(stripe_subscriptions, :val)",
            ExpressionAttributeValues={
                ":val": [subscription_id]
            }
        )
    
    def get_best_subscription(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        self._update_payment_info()
        return self.best_subscription
