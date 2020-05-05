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
    
    def _refresh(self, force=False, alert_if_not_in_dynamodb=False):
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
                raise TeamNotInDynamoDBError("Unauthorized team: " + self.id)
            else:
                return
        self.is_in_dynamodb = True
        self.best_subscription = None
        date = response['Item']['payment_expiration']
        try:
            self.payment_expiration = datetime.strptime(date, DATETIME_FORMAT)
        except:
            # The expiration is probably "never".
            self.payment_expiration = date
        self.payment_plan = response['Item']['payment_plan']
        self.subscriptions = []
        for id in response['Item'].get('stripe_subscriptions', []):
            self.add_subscription(id, add_to_dynamodb=False)
    
    def is_trialing(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.payment_plan == "trial"
    
    def get_time_till_payment_is_due(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        if self.payment_expiration == "never":
            return timedelta(years=1000000)
        now = datetime.utcnow()
        return self.payment_expiration - now
    
    def get_time_payment_has_been_overdue(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        if self.payment_expiration == "never":
            return 0
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
            'enterprise_id': enterprise_id,
            'create_time': create_time.strftime(DATETIME_FORMAT),
            'payment_expiration': trial_expiration.strftime(DATETIME_FORMAT),
            'payment_plan': "trial"
        }
        for key in list(item):
            if not item[key]:
                del item[key]
        self.table.put_item(Item=item)
        self._refresh(force=True)
    
    def add_subscription(self, subscription_id, add_to_dynamodb=True):
        # Note as of 2020-05-02: There should only be one subscription
        # for each team, but in the case that there are multiple,
        # I want DynamoDB to keep track for debugging/support purposes.
        # The "best_subscription" is the one that expires latest.
        self._refresh(alert_if_not_in_dynamodb=True)
        subscription = StripeSubscription(subscription_id)
        self.subscriptions.append(subscription)
        self.best_subscription = max(self.subscriptions)
        if (self.payment_expiration == "never"
            or not self.best_subscription.is_current()):
            return
        self.payment_expiration = self.best_subscription.get_expiration()
        self.payment_plan = self.best_subscription.get_plan_nickname()
        if add_to_dynamodb:
            if len(self.subscriptions) == 1:
                self.table.update_item(
                    Key={
                        'PK': "TEAM#" + self.id,
                        'SK': "team"
                    },
                    UpdateExpression=
                        "SET payment_expiration = :val,"
                        " payment_plan = :val2,"
                        " stripe_subscriptions = :val3",
                    ExpressionAttributeValues={
                        ":val": self.payment_expiration.strftime(DATETIME_FORMAT),
                        ":val2": self.payment_plan,
                        ":val3": [subscription_id]
                    }
                )
            else:
                self.table.update_item(
                    Key={
                        'PK': "TEAM#" + self.id,
                        'SK': "team"
                    },
                    UpdateExpression=
                        "SET payment_expiration = :val,"
                        " payment_plan = :val2,"
                        " stripe_subscriptions = list_append(stripe_subscriptions, :val3)",
                    ExpressionAttributeValues={
                        ":val": self.payment_expiration.strftime(DATETIME_FORMAT),
                        ":val2": self.payment_plan,
                        ":val3": [subscription_id]
                    }
                )
