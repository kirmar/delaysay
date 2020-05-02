import boto3
import time
import os
from datetime import datetime

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class Team:
    
    def __init__(self, id):
        assert isinstance(id, str)
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
            if alert_if_not_in_dynamodb:
                raise TeamNotInDynamoDBError(
                    "Team did not authorize: " + self.id)
            self.is_in_dynamodb = False
            self.payment_expiration = None
            self.subscription_id = None
            self.payment_plan_nickname = None
        else:
            self.is_in_dynamodb = True
            expiration_string = response['Item']['payment_expiration']
            try:
                self.payment_expiration = datetime.strptime(
                    expiration_string, DATETIME_FORMAT)
            except:
                self.payment_expiration = expiration_string
            self.subscription_id = response['Item'].get('stripe_subscription_id')
            self.payment_plan_nickname = response['Item']['payment_plan']
    
    def never_needs_to_pay(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.payment_expiration == "never"
    
    def is_trialing(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.payment_plan_nickname == "trial"
    
    def get_payment_expiration(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.payment_expiration
    
    def get_subscription_id(self):
        self._refresh(alert_if_not_in_dynamodb=True)
        return self.subscription_id
    
    def add_to_dynamodb(self, team_name, enterprise_id, create_time,
                        payment_expiration):
        self._refresh()
        if self.is_in_dynamodb:
            return
        item = {
            'PK': "TEAM#" + self.id,
            'SK': "team",
            'team_name': team_name,
            'enterprise_id': enterprise_id,
            'create_time': create_time,
            'payment_expiration': payment_expiration,
            'payment_plan': "trial"
        }
        for key in list(item):
            if not item[key]:
                del item[key]
        self.table.put_item(Item=item)
        self._refresh(force=True)
    
    def update_payment_info(self, payment_expiration, payment_plan,
                            stripe_subscription_id):
        assert payment_expiration and payment_plan and stripe_subscription_id
        self.table.update_item(
            Key={
                'PK': "TEAM#" + self.id,
                'SK': "team"
            },
            UpdateExpression="SET payment_expiration = :val,"
                             " payment_plan = :val2,"
                             " stripe_subscription_id = :val3",
            ExpressionAttributeValues={
                ":val": payment_expiration,
                ":val2": payment_plan,
                ":val3": stripe_subscription_id
            }
        )
        self._refresh(force=True)
