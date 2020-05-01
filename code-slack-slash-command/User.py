import boto3
import time
import requests
import json
import os
import aws_encryption_sdk
from DelaySayExceptions import UserAuthorizeError
from datetime import timezone, timedelta

kms_key_provider = aws_encryption_sdk.KMSMasterKeyProvider(key_ids=[
    os.environ['KMS_MASTER_KEY_ARN']
])

def decrypt_oauth_token(encrypted_token):
    token_as_bytes, decryptor_header = aws_encryption_sdk.decrypt(
        source=encrypted_token,
        key_provider=kms_key_provider
    )
    token = token_as_bytes.decode()
    return token

class User:
    
    def __init__(self, id):
        assert isinstance(id, str)
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])
        self.id = id
        self.token = None
        self.timezone = None
    
    def get_auth_token(self):
        if not self.token:
            response = self.table.get_item(
                Key={
                    'PK': "USER#" + self.id,
                    'SK': "user"
                }
            )
            try:
                encrypted_token_as_boto3_binary = response['Item']['token']
            except KeyError:
                raise UserAuthorizeError("User did not authorize")
            encrypted_token_as_bytes = encrypted_token_as_boto3_binary.value
            self.token = decrypt_oauth_token(encrypted_token_as_bytes)
        return self.token

    def get_timezone(self):
        if not self.timezone:
            r = requests.post(
                url="https://slack.com/api/users.info",
                data={
                    'user': self.id
                },
                headers={
                    'Content-Type': "application/x-www-form-urlencoded",
                    'Authorization': "Bearer " + self.token
                }
            )
            if r.status_code != 200:
                print(r.status_code, r.reason)
                raise Exception("requests.post failed")
            user_object = json.loads(r.content)
            if not user_object['ok']:
                raise Exception(
                    "User.get_timezone() failed: " + user_object['error'] +
                    "\nFor more information, see here:"
                    "\nhttps://api.slack.com/methods/users.info")
            tz_offset = user_object['user']['tz_offset']
            self.timezone = timezone(timedelta(seconds=tz_offset))
        return self.timezone
