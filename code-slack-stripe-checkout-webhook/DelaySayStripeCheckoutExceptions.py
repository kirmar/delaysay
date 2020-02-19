class TeamNotInDynamoDBError(Exception):
    pass

class NoTeamIdGivenError(Exception):
    pass

class SignaturesDoNotMatchError(Exception):
    pass

class TimeToleranceExceededError(Exception):
    pass
