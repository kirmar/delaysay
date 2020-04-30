class TeamNotInDynamoDBError(Exception):
    pass

class StripeSubscriptionDoesNotExistError(Exception):
    pass

class NoTeamIdGivenError(Exception):
    pass

class SignaturesDoNotMatchError(Exception):
    pass

class TimeToleranceExceededError(Exception):
    pass
