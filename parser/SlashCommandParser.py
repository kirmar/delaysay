#!/usr/bin/env python3.7

import re
from datetime import datetime, timedelta
from dateparser import parse as dateparser_parse
from dateutil.parser import parse as dateutil_parse

SECONDS_THRESHOLD = timedelta(minutes=10)

class TimeParseError(Exception):
    pass

class SlashCommandParser:
    
    def __init__(self, command_text, initial_time=None):
        assert isinstance(command_text, str)
        assert isinstance(initial_time, datetime) or not initial_time
        if initial_time:
            self.initial_time = initial_time
        else:
            self.initial_time = datetime.now()
        self.command_text = command_text
        self.time, self.date_string, self.time_string = self._parse_time()
        self.message = self._parse_message()
    
    def _parse_time(self):
        original_user_input = self.command_text.split("say", 1)[0]
        user_input = original_user_input.rstrip(":,")
        user_input = user_input.replace("hr", "hour").replace("h ", "hour ")
        user_input = user_input.replace("a ", "am ")
        user_input = user_input.replace("next", "")
        scheduled_time = dateparser_parse(
            user_input,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': self.initial_time
            }
        )
        if not scheduled_time:
            try:
                scheduled_time = dateutil_parse(
                    user_input, default=self.initial_time)
            except ValueError:
                raise TimeParseError(
                    f"Cannot parse time '{original_user_input}'")
        elif scheduled_time <= self.initial_time:
            # Help dateparser.parser.parse with relative dates
            scheduled_time = dateparser_parse(
                "in " + user_input,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': self.initial_time
                }
            )
        if not scheduled_time:
            raise TimeParseError(f"Cannot parse time '{original_user_input}'")
        date_string = scheduled_time.strftime("%Y-%m-%d")
        if scheduled_time - self.initial_time > SECONDS_THRESHOLD:
            scheduled_time = scheduled_time.replace(second=0)
            time_string = scheduled_time.strftime("%I:%M %p")
        else:
            time_string = scheduled_time.strftime("%I:%M:%S %p")
        time_string = re.sub(r"^0(?=[0-9]:)", "", time_string)
        return (scheduled_time, date_string, time_string)
    
    def get_time(self):
        return self.time
    
    def get_date_string(self):
        return self.date_string
    
    def get_time_string(self):
        return self.time_string
    
    def _parse_message(self):
        message = self.command_text.split("say", 1)[1]
        message = message.lstrip(":,").strip().strip("'").strip('"')
        return message
    
    def get_message(self):
        return self.message
