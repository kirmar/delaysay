#!/usr/bin/env python3.7

import sys, os
sys.path.insert(
    1, os.path.dirname(os.path.realpath(__file__)) + '/../code')

import unittest
from datetime import datetime, timezone, timedelta
from SlashCommandParser import SlashCommandParser, TimeParseError

class SlashCommandParserTestCase(unittest.TestCase):

    def setUp(self):
        self.pst = timezone(timedelta(hours=-8))
        self.est = timezone(timedelta(hours=-5))
        self.gmt = timezone(timedelta(hours=0))
        self.ist = timezone(timedelta(hours=5, minutes=30))
        self.fjt = timezone(timedelta(hours=12))

    def test_relative_time_parser(self):
        initial_time = datetime(2019, 8, 19, 5, 17, 5, tzinfo=self.ist)

        # 1 hour (-5 sec just because
        # "I think that's what the date parser module did" - Kira)
        time_elapsed = timedelta(hours=1, seconds=-5)
        p = SlashCommandParser("1 hour say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("1 hr say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("1hr say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("1 h say Hm...", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("in 1h say Hm...", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)


        # 2 hours
        time_elapsed = timedelta(hours=2, seconds=-5)
        p = SlashCommandParser("2 hours say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 2 hours, 30 minutes
        # time_elapsed = timedelta(hours=2, minutes=30)
        # p = SlashCommandParser("2.5hrs say Take a break", initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 minute
        time_elapsed = timedelta(minutes=1)
        p = SlashCommandParser("1 minute say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 3 minutes
        time_elapsed = timedelta(minutes=3)
        p = SlashCommandParser("3 minutes say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("3min say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 hour, 30 minutes
        time_elapsed = timedelta(hours=1, minutes=30, seconds=-5)
        p = SlashCommandParser("90 min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 30 seconds
        time_elapsed = timedelta(seconds=30)
        p = SlashCommandParser("30 seconds say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("30sec say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 hour, 15 minutes
        time_elapsed = timedelta(hours=1, minutes=15, seconds=-5)
        p = SlashCommandParser("1hr 15min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 day
        time_elapsed = timedelta(days=1, seconds=-5)
        p = SlashCommandParser("1 day say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("Tomorrow say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        p = SlashCommandParser("tomorrow say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 2 days
        time_elapsed = timedelta(days=2, seconds=-5)
        p = SlashCommandParser("2 days say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 day, 50 minutes
        time_elapsed = timedelta(days=1, minutes=50, seconds=-5)
        p = SlashCommandParser("1 day 50 min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 0.9 days, 0.9 hours, 0.9 minutes, 50 seconds
        # time_elapsed = timedelta(
        #     days=0.9, hours=0.9, minutes=0.9, seconds=50)
        # p = SlashCommandParser(
        #     "0.9 days 0.9 hours 0.9 minutes 50 seconds say Take a break",
        #     initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)

        # 1 week
        # time_elapsed = timedelta(weeks=1)
        # p = SlashCommandParser("next week say Take a break", initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)

    def test_relatively_absolute_time_parser(self):
        initial_time = datetime(2019, 8, 19, 3, 17, 5, tzinfo=self.gmt)

        # Next Monday
        final_datetime = datetime(2019, 8, 26, 0, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("monday say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("next monday say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # The next occurrence of 8:00am
        final_datetime = datetime(2019, 8, 19, 8, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("8 a.m. say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("8 am say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("8am say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("8a say Hm...", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        final_datetime = datetime(2019, 8, 20, 8, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser(
            "8 a.m. say Take a break",
            datetime(2019, 8, 19, 8, 17, 5, tzinfo=self.gmt))
        self.assertEqual(p.get_time(), final_datetime)

        # The next occurrence of 8:30pm
        final_datetime = datetime(2019, 8, 19, 20, 30, 0, tzinfo=self.gmt)
        p = SlashCommandParser("8:30pm say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # The next occurrence of 12:00pm
        final_datetime = datetime(2019, 8, 19, 12, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("noon say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        with self.assertRaises(TimeParseError):
            # TODO: Fix this, then find another example that should
            # raise the TimeParseError.
            final_datetime = datetime(2019, 8, 19, 12, 0, 0, tzinfo=self.gmt)
            p = SlashCommandParser("Tomorrow 12noon say Blah", initial_time)

        final_datetime = datetime(2019, 8, 20, 12, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("Tomorrow 12 noon say Blah", initial_time)
        print(p.get_time(), final_datetime)
        self.assertEqual(p.get_time(), final_datetime)
        
        final_datetime = datetime(2019, 8, 19, 12, 0, 0, tzinfo=self.pst)
        p = SlashCommandParser("12 noon PST say Blah", initial_time)
        print(p.get_time(), final_datetime)
        self.assertEqual(p.get_time(), final_datetime)

        # TODO: Why does the time not work if the user says both
        # "Tomorrow" and "PST"?
        # final_datetime = datetime(2019, 8, 20, 12, 0, 0, tzinfo=self.pst)
        # p = SlashCommandParser("Tomorrow 12 noon PST say Blah", initial_time)
        # print(p.get_time(), final_datetime)
        # self.assertEqual(p.get_time(), final_datetime)

        final_datetime = datetime(2019, 8, 19, 12, 0, 0, tzinfo=self.pst)
        p = SlashCommandParser("12 noon PST say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # The next occurrence of 12:00am
        final_datetime = datetime(2019, 8, 20, 0, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("midnight say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # Tomorrow, 12:00pm
        final_datetime = datetime(2019, 8, 20, 12, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("noon tomorrow say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("tomorrow noon say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("tomorrow at noon say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # Next Monday, 8:00am
        final_datetime = datetime(2019, 8, 26, 8, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("monday 8am say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("mon at 8 am say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # Tomorrow, 8:00am
        final_datetime = datetime(2019, 8, 20, 8, 0, 0, tzinfo=self.gmt)
        p = SlashCommandParser("tomorrow 8am say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("8a tomorrow say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

    def test_absolute_time_parser(self):
        initial_time = datetime(2019, 8, 19, 3, 17, 5, tzinfo=self.fjt)

        # September 1, 2019
        final_datetime = datetime(2019, 9, 1, 0, 0, 0, tzinfo=self.fjt)
        p = SlashCommandParser("september 1 say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("sep 1 say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("sep 1, 2019 say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("sep 1 2019 say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("1 sep say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("2019-09-01 say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("09-01 say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("9/1 say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("2019/09/01 say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        p = SlashCommandParser("09/01/2019 say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # September 1, 2019, 8:00am
        final_datetime = datetime(2019, 9, 1, 8, 0, 0, tzinfo=self.fjt)
        p = SlashCommandParser("8a sep 1 say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # September 1, 2019, 2:35pm
        final_datetime = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.fjt)
        p = SlashCommandParser("2019-09-01 14:35 say Humbug", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

    def test_timezones(self):
        with self.assertRaises(AssertionError):
            initial_time = datetime(2019, 9, 1, 14, 35, 0, tzinfo=None)
            p = SlashCommandParser("2019-09-01 14:35 say Humbug", initial_time)
        
        # September 1, 2019, 2:35pm
        initial_time = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.est)
        final_datetime = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.est)
        p = SlashCommandParser("2019-09-01 14:35 say Humbug", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # September 1, 2019, 2:35pm PST from PST
        initial_time = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.est)
        final_datetime = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.pst)
        p = SlashCommandParser(
            "2019-09-01 14:35 PST say Humbug", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

        # September 1, 2019, 2:35pm GMT from PST
        initial_time = datetime(2019, 9, 1, 14, 35, 0, tzinfo=self.est)
        final_datetime = datetime(2019, 9, 1, 14, 35, 30, tzinfo=self.gmt)
        p = SlashCommandParser("2019-09-01T14:35:30Z say Humbug", initial_time)
        self.assertEqual(p.get_time(), final_datetime)

    def test_date_and_time_strings(self):
        initial_time = datetime(2019, 8, 19, 3, 17, 59, tzinfo=self.est)

        p = SlashCommandParser("1 hour say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-19")
        self.assertEqual(p.get_time_string().lower(), "4:17 am")

        p = SlashCommandParser("3 min say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-19")
        self.assertEqual(p.get_time_string().lower(), "3:20:59 am")

        p = SlashCommandParser("30 seconds say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-19")
        self.assertEqual(p.get_time_string().lower(), "3:18:29 am")

        p = SlashCommandParser("2 days 50 min say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-21")
        self.assertEqual(p.get_time_string().lower(), "4:07 am")

        p = SlashCommandParser("monday say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-26")
        self.assertEqual(p.get_time_string().lower(), "12:00 am")
        # self.assertEqual(p.get_time_string().lower(), "3:18 am")

        p = SlashCommandParser("8 p.m. say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-19")
        self.assertEqual(p.get_time_string().lower(), "8:00 pm")

        p = SlashCommandParser("september 1 say meh", initial_time)
        self.assertEqual(p.get_date_string(), "2019-09-01")
        self.assertEqual(p.get_time_string().lower(), "12:00 am")
        # self.assertEqual(p.get_time_string().lower(), "3:18 am")

        p = SlashCommandParser("2019-09-01 14:30 say Take break", initial_time)
        self.assertEqual(p.get_date_string(), "2019-09-01")
        self.assertEqual(p.get_time_string().lower(), "2:30 pm")
        
        p = SlashCommandParser("12 noon PST say Blah", initial_time)
        self.assertEqual(p.get_date_string(), "2019-08-19")
        self.assertEqual(p.get_time_string().lower(), "12:00 pm pst")

    def test_date_and_time_strings_for_slack(self):
        raise Exception("Unit test not yet implemented")

    def test_message_parser(self):
        initial_time = datetime(2000, 1, 1, 21, 30, 0, tzinfo=self.est)
        
        p = SlashCommandParser("8am say hello world", initial_time)
        self.assertEqual(p.get_message(), "hello world")

        p = SlashCommandParser(
            "September 2nd, at 6:00, say 'Hello, world!'", initial_time)
        self.assertEqual(p.get_message(), "Hello, world!")

        p = SlashCommandParser(
            "1 hour say What did Sally say yesterday?", initial_time)
        self.assertEqual(p.get_message(), "What did Sally say yesterday?")

        p = SlashCommandParser(
            "1 hour say: I did say that.", initial_time)
        self.assertEqual(p.get_message(), "I did say that.")

        p = SlashCommandParser(
            "1 hour say ... ??? ...", initial_time)
        self.assertEqual(p.get_message(), "... ??? ...")

if __name__ == '__main__':
    unittest.main()
