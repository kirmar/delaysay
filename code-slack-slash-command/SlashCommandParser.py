import re
from DelaySayExceptions import CommandParseError, TimeParseError
from datetime import datetime, timedelta
from dateparser import parse

SECONDS_THRESHOLD = timedelta(minutes=10)

class SlashCommandParser:
    
    def __init__(self, command_text, initial_time):
        assert isinstance(command_text, str)
        assert isinstance(initial_time, datetime)
        assert bool(initial_time.tzinfo)
        self.initial_time = initial_time
        self.user_tz = initial_time.tzinfo
        self.command_text = command_text
        try:
            self.original_time, self.original_message = (
                self.command_text.split("say", 1))
        except ValueError:
            raise CommandParseError(
                self.command_text,
                f'Cannot parse time and message from "{self.command_text}"')
        self.time, self.force_timezone = self._parse_time()
        self.message = self._parse_message()
        self.date_string = None
        self.time_string = None
        self.date_string_for_slack = None
        self.time_string_for_slack = None
    
    def _has_seconds(self):
        return int(self.time.strftime("%S")) != 0
    
    def _remove_leading_zero_from_hour(self, time_string):
        # Remove leading zeroes from the hour.
        return re.sub(r"^0(?=[0-9]:)", "", time_string)
    
    def _parse_time(self):
        user_input = self.original_time.rstrip(":").rstrip(",")
        user_input = user_input.replace("hr", "hour").replace("h ", "hour ")
        user_input = user_input.replace("a ", "am ")
        user_input = user_input.replace("next", "")
        scheduled_time = parse(
            user_input,
            settings={
                'PREFER_DATES_FROM': "future",
                'RELATIVE_BASE': self.initial_time.replace(tzinfo=None)
            }
        )
        if not scheduled_time:
            raise TimeParseError(
                self.original_time,
                f'Cannot parse time "{self.original_time}"')
        force_timezone = bool(scheduled_time.tzinfo)
        if not scheduled_time.tzinfo:
            scheduled_time = scheduled_time.replace(tzinfo=self.user_tz)
        if scheduled_time <= self.initial_time:
            # Help dateparser.parser.parse with relative dates
            scheduled_time = parse(
                "in " + user_input,
                settings={
                    'PREFER_DATES_FROM': "future",
                    'RELATIVE_BASE': self.initial_time.replace(tzinfo=None)
                }
            )
            if not scheduled_time:
                raise TimeParseError(
                    self.original_time,
                    f'Cannot parse time "{self.original_time}"')
            force_timezone = bool(scheduled_time.tzinfo)
            if not scheduled_time.tzinfo:
               scheduled_time = scheduled_time.replace(tzinfo=self.user_tz)
        if scheduled_time - self.initial_time > SECONDS_THRESHOLD:
            scheduled_time = scheduled_time.replace(second=0)
        return (scheduled_time, force_timezone)
    
    def _compose_datetime_strings_for_slack(self):
        # timestamp: seconds since January 1, 1970, 00:00:00 UTC
        timestamp = int(self.time.timestamp())
        
        # Set the date string
        date_string = "<!date^" + str(timestamp) + "^{date_long}|"
        date_string += self.time.strftime("%Y-%m-%d")
        date_string += ">"
        
        # Set the time string
        if self._has_seconds():
            time_string = "<!date^" + str(timestamp) + "^{time_secs}|"
            time_string += self.time.strftime("%I:%M:%S %Z")
            time_string += ">"
        else:
            time_string = "<!date^" + str(timestamp) + "^{time}|"
            time_string += self.time.strftime("%I:%M %Z")
            time_string += ">"
        time_string = self._remove_leading_zero_from_hour(time_string)
        
        return (date_string, time_string)
    
    def get_time(self):
        return self.time
    
    def get_date_string(self):
        if not self.date_string:
            self.date_string = self.time.strftime("%Y-%m-%d")
        return self.date_string
    
    def get_time_string(self):
        if not self.time_string:
            time_string = self.time.strftime("%I:%M")
            if self._has_seconds():
                time_string += self.time.strftime(":%S")
            time_string += self.time.strftime(" %p")
            time_string = self._remove_leading_zero_from_hour(time_string)
            if self.force_timezone or self.time.tzinfo != self.user_tz:
                # Although I think if self.time.tzinfo != self.user_tz,
                # then self.force_timezone will be True.
                time_string += self.time.strftime(" %Z")
            self.time_string = time_string
        return self.time_string
    
    def get_date_string_for_slack(self):
        if not self.date_string_for_slack:
            self.date_string_for_slack, self.time_string_for_slack = (
                self._compose_datetime_strings_for_slack())
        return self.date_string_for_slack
    
    def get_time_string_for_slack(self):
        if not self.time_string_for_slack:
            self.date_string_for_slack, self.time_string_for_slack = (
                self._compose_datetime_strings_for_slack())
        return self.time_string_for_slack
    
    def _parse_message(self):
        return self.original_message.lstrip(":,").strip().strip("'").strip('"')
    
    def get_message(self):
        return self.message
