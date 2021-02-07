import boto3
import time
import os
from DelaySayExceptions import BillingTokenInvalidError
from datetime import datetime

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class BillingToken:
    
    def __init__(self, token):
        assert isinstance(token, str) or token == None
        if token == "" or token == None:
            raise BillingTokenInvalidError(
                "Billing token empty: " + str(token))
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])
        self.token = token
        self.table_entry = None
    
    def _get_table_entry(self):
        if not self.table_entry:
            response = self.table.get_item(
                Key={
                    'PK': "BILLING#" + self.token,
                    'SK': "billing"
                    }
            )
            if 'Item' not in response:
                raise BillingTokenInvalidError(
                    "Billing token invalid: " + self.token)
            self.table_entry = response['Item']
        return self.table_entry
    
    def add_to_dynamodb(self, create_time, expiration_period, team_id,
                        team_domain, user_id):
        expiration = create_time + expiration_period
        item = {
            'PK': "BILLING#" + self.token,
            'SK': "billing",
            'token': self.token,
            'create_time': create_time.strftime(DATETIME_FORMAT),
            'token_expiration': expiration.strftime(DATETIME_FORMAT),
            'team_id': team_id,
            'team_domain': team_domain,
            'user_id': user_id
        }
        for key in list(item):
            if not item[key]:
                del item[key]
        self.table.put_item(Item=item)
    
    def has_expired(self):
        date = self._get_table_entry()['token_expiration']
        token_expiration = datetime.strptime(date, DATETIME_FORMAT)
        now = datetime.utcnow()
        return (token_expiration < now)
    
    def get_team_id(self):
        team_id = self._get_table_entry()['team_id']
        return team_id
    
    def __str__(self):
        return self.token
