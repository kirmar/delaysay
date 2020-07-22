from datetime import datetime

class Datetime:
    
    def __init__(self):
        pass
    
    def get_datetime(self):
        pass
    
    def get_slack_string(self):
        pass
    
    def get_iso_string(self):
        # This is the format used to log dates in the DynamoDB table.
        DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        pass
