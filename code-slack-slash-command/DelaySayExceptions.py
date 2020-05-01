class SlackSignaturesDoNotMatchError(Exception):
    pass

class SlackSignatureTimeToleranceExceededError(Exception):
    pass

class UserAuthorizeError(Exception):
    pass

class CommandParseError(Exception):
    def __init__(self, command_text, message):
        super().__init__(message)
        self.command_text = command_text

class TimeParseError(Exception):
    def __init__(self, time_text, message):
        super().__init__(message)
        self.time_text = time_text
