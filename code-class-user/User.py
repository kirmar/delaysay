import boto3
import time
import requests
import json
import os
import aws_encryption_sdk
from aws_encryption_sdk import CommitmentPolicy
from DelaySayExceptions import UserAuthorizeError
from datetime import timezone, timedelta

encryption_client = aws_encryption_sdk.EncryptionSDKClient(
    commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT
)
kms_key_provider = aws_encryption_sdk.StrictAwsKmsMasterKeyProvider(
    key_ids=[
        os.environ['KMS_MASTER_KEY_ARN']
    ]
)

# This is the format used to log dates in the DynamoDB table.
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def encrypt_oauth_token(token):
    token_as_bytes = token.encode()
    encrypted_token, encryptor_header = encryption_client.encrypt(
        source=token_as_bytes,
        key_provider=kms_key_provider
    )
    return encrypted_token

def decrypt_oauth_token(encrypted_token):
    token_as_bytes, decryptor_header = encryption_client.decrypt(
        source=encrypted_token,
        key_provider=kms_key_provider
    )
    token = token_as_bytes.decode()
    return token

class User:
    
    def __init__(self, id):
        assert id and isinstance(id, str)
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ['AUTH_TABLE_NAME'])
        self.id = id
        self._reset()
    
    def _reset(self):
        self.token = None
        self.timezone = None
    
    def _reencrypt_token_with_key_commitment(self):
        token_encrypted_with_key_commitment = encrypt_oauth_token(self.token)
        self.table.update_item(
            Key={
                'PK': "USER#" + self.id,
                'SK': "user"
            },
            UpdateExpression=
                "SET #t = :val",
            ExpressionAttributeValues={
                ":val": token_encrypted_with_key_commitment
            },
            ExpressionAttributeNames={
                "#t": "token"
            }
        )
    
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
                raise UserAuthorizeError("Unauthorized user: " + self.id)
            encrypted_token_as_bytes = encrypted_token_as_boto3_binary.value
            self.token = decrypt_oauth_token(encrypted_token_as_bytes)
            self._reencrypt_token_with_key_commitment()
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
    
    
    def add_to_dynamodb(self, token, team_id, team_name, enterprise_id,
                        create_time):
        item = {
            'PK': "USER#" + self.id,
            'SK': "user",
            'token': encrypt_oauth_token(token),
            'user_id': self.id,
            'team_name': team_name,
            'team_id': team_id,
            'enterprise_id': enterprise_id,
            'create_time': create_time.strftime(DATETIME_FORMAT)
        }
        for key in list(item):
            if not item[key]:
                del item[key]
        self.table.put_item(Item=item)
        self._reset()