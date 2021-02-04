# General exceptions

class UserAuthorizeError(Exception):
    pass

class TeamNotInDynamoDBError(Exception):
    pass


# Slash command exceptions

class SlackSignaturesDoNotMatchError(Exception):
    pass

class SlackSignatureTimeToleranceExceededError(Exception):
    pass

class CommandParseError(Exception):
    def __init__(self, command_text, message):
        super().__init__(message)
        self.command_text = command_text

class TimeParseError(Exception):
    def __init__(self, time_text, message):
        super().__init__(message)
        self.time_text = time_text


# Stripe webhook exceptions

class StripeSubscriptionDoesNotExistError(Exception):
    pass

class NoTeamIdGivenError(Exception):
    pass

class SignaturesDoNotMatchError(Exception):
    pass

class TimeToleranceExceededError(Exception):
    pass
