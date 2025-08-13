from DelaySayExceptions import BillingTokenInvalidError
from datetime import datetime, timezone

class BillingToken:
    
    def __init__(self, token):
        assert isinstance(token, str) or token == None
        from dynamodb import dynamodb_table, DATETIME_FORMAT
        if token == "" or token == None:
            raise BillingTokenInvalidError(
                "Billing token empty: " + str(token))
        self.table = dynamodb_table
        self.datetime_format = DATETIME_FORMAT
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
            'create_time': create_time.strftime(self.datetime_format),
            'token_expiration': expiration.strftime(self.datetime_format),
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
        token_expiration = datetime.strptime(date, self.datetime_format)
        now = datetime.now(timezone.utc)
        return (token_expiration < now)
    
    def get_team_id(self):
        team_id = self._get_table_entry()['team_id']
        return team_id
    
    def __str__(self):
        return self.token
