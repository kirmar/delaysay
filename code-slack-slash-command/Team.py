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
    
    def _refresh(self):
        if time.time() - self.last_updated < 2:
            return
        self.last_updated = time.time()
        response = self.table.get_item(
            Key={
                'PK': "TEAM#" + self.id,
                'SK': "team"
                }
        )
        if 'Item' not in response:
            raise TeamNotInDynamoDBError("Team did not authorize: " + self.id)
        expiration_string = response['Item']['payment_expiration']
        try:
            self.payment_expiration = datetime.strptime(
                expiration_string, DATETIME_FORMAT)
        except:
            self.payment_expiration = expiration_string
        self.subscription_id = response['Item'].get('stripe_subscription_id')
        self.payment_plan_nickname = response['Item']['payment_plan']
    
    def never_needs_to_pay(self):
        self._refresh()
        return self.payment_expiration == "never"
    
    def is_trialing(self):
        self._refresh()
        return self.payment_plan_nickname == "trial"
    
    def get_payment_expiration(self):
        self._refresh()
        return self.payment_expiration
    
    def get_subscription_id(self):
        self._refresh()
        return self.subscription_id
    
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
        self._refresh()
