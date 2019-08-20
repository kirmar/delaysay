#!/usr/bin/env python3.7

import sys, os
sys.path.insert(1, os.path.dirname(os.path.realpath(__file__)) + '/../delaysay')

import unittest
import datetime
# from dateutil.tz import tzutc
from SlashCommandParser import SlashCommandParser

class SlashCommandParserTestCase(unittest.TestCase):
    
    def test_relative_time_parser(self):
        initial_time = datetime.datetime(2019, 8, 19, 5, 17, 5)
    
        # 1 hour
        time_elapsed = datetime.timedelta(hours=1, seconds=-5)
        p = SlashCommandParser("1 hour say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("1 hr say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("1hr say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("1 h say Hm...", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 2 hours
        time_elapsed = datetime.timedelta(hours=2, seconds=-5)
        p = SlashCommandParser("2 hours say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 2 hours, 30 minutes
        # time_elapsed = datetime.timedelta(hours=2, minutes=30)
        # p = SlashCommandParser("2.5hrs say Take a break", initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 minute
        time_elapsed = datetime.timedelta(minutes=1)
        p = SlashCommandParser("1 minute say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 3 minutes
        time_elapsed = datetime.timedelta(minutes=3)
        p = SlashCommandParser("3 minutes say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("3min say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 hour, 30 minutes
        time_elapsed = datetime.timedelta(hours=1, minutes=30, seconds=-5)
        p = SlashCommandParser("90 min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 30 seconds
        time_elapsed = datetime.timedelta(seconds=30)
        p = SlashCommandParser("30 seconds say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("30sec say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 hour, 15 minutes
        time_elapsed = datetime.timedelta(hours=1, minutes=15, seconds=-5)
        p = SlashCommandParser("1hr 15min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 day
        time_elapsed = datetime.timedelta(days=1, seconds=-5)
        p = SlashCommandParser("1 day say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("Tomorrow say Blah", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        p = SlashCommandParser("tomorrow say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 2 days
        time_elapsed = datetime.timedelta(days=2, seconds=-5)
        p = SlashCommandParser("2 days say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 day, 50 minutes
        time_elapsed = datetime.timedelta(days=1, minutes=50, seconds=-5)
        p = SlashCommandParser("1 day 50 min say Take a break", initial_time)
        self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 0.9 days, 0.9 hours, 0.9 minutes, 50 seconds
        # time_elapsed = datetime.timedelta(days=0.9, hours=0.9, minutes=0.9, seconds=50)
        # p = SlashCommandParser(
        #     "0.9 days 0.9 hours 0.9 minutes 50 seconds say Take a break",
        #     initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
        # 1 week
        # time_elapsed = datetime.timedelta(weeks=1)
        # p = SlashCommandParser("next week say Take a break", initial_time)
        # self.assertEqual(p.get_time(), initial_time + time_elapsed)
    
    def test_relatively_absolute_time_parser(self):
        initial_time = datetime.datetime(2019, 8, 19, 3, 17, 5)
        
        # Next Monday
        final_datetime = datetime.datetime(2019, 8, 26, 0, 0, 0)
        p = SlashCommandParser("monday say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("next monday say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # The next occurrence of 8:00am
        final_datetime = datetime.datetime(2019, 8, 19, 8, 0, 0)
        p = SlashCommandParser("8 a.m. say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("8 am say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("8am say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("8a say Hm...", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        final_datetime = datetime.datetime(2019, 8, 20, 8, 0, 0)
        p = SlashCommandParser("8 a.m. say Take a break",
                               datetime.datetime(2019, 8, 19, 8, 17, 5))
        self.assertEqual(p.get_time(), final_datetime)
        
        # The next occurrence of 8:30pm
        final_datetime = datetime.datetime(2019, 8, 19, 20, 30, 0)
        p = SlashCommandParser("8:30pm say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # The next occurrence of 12:00pm
        final_datetime = datetime.datetime(2019, 8, 19, 12, 0, 0)
        p = SlashCommandParser("noon say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # final_datetime = datetime.datetime(2019, 8, 19, 12, 0, 0)
        # p = SlashCommandParser("12noon say Blah", initial_time)
        # self.assertEqual(p.get_time(), final_datetime)
        
        # The next occurrence of 12:00am
        final_datetime = datetime.datetime(2019, 8, 20, 0, 0, 0)
        p = SlashCommandParser("midnight say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # Tomorrow, 12:00pm
        final_datetime = datetime.datetime(2019, 8, 20, 12, 0, 0)
        p = SlashCommandParser("noon tomorrow say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("tomorrow noon say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("tomorrow at noon say Hi, there!", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # Next Monday, 8:00am
        final_datetime = datetime.datetime(2019, 8, 26, 8, 0, 0)
        p = SlashCommandParser("monday 8am say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("mon at 8 am say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # Tomorrow, 8:00am
        final_datetime = datetime.datetime(2019, 8, 20, 8, 0, 0)
        p = SlashCommandParser("tomorrow 8am say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        p = SlashCommandParser("8a tomorrow say Blah", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
    
    def test_absolute_time_parser(self):
        initial_time = datetime.datetime(2019, 8, 19, 3, 17, 5)
        
        # September 1, 2019
        final_datetime = datetime.datetime(2019, 9, 1, 0, 0, 0)
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
        final_datetime = datetime.datetime(2019, 9, 1, 8, 0, 0)
        p = SlashCommandParser("8a sep 1 say Take a break", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # September 1, 2019, 2:35pm
        final_datetime = datetime.datetime(2019, 9, 1, 14, 35, 0)
        p = SlashCommandParser("2019-09-01 14:35 say Humbug", initial_time)
        self.assertEqual(p.get_time(), final_datetime)
        
        # September 1, 2019, 2:35pm GMT
        # final_datetime = datetime.datetime(
        #     2019, 9, 1, 14, 35, 30, tzinfo=tzutc())
        # p = SlashCommandParser(
        #    "2019-09-01T14:35:30Z say Humbug", initial_time)
        # self.assertEqual(p.get_time(), final_datetime)
    
    def test_date_and_time_strings(self):
        initial_time = datetime.datetime(2019, 8, 19, 3, 17, 59)
        
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
        
        p = SlashCommandParser("september 1 say meh")
        self.assertEqual(p.get_date_string(), "2019-09-01")
        self.assertEqual(p.get_time_string().lower(), "12:00 am")
        # self.assertEqual(p.get_time_string().lower(), "3:18 am")
        
        p = SlashCommandParser("2019-09-01 14:30 say Take break")
        self.assertEqual(p.get_date_string(), "2019-09-01")
        self.assertEqual(p.get_time_string().lower(), "2:30 pm")
    
    def test_message_parser(self):
        p = SlashCommandParser("8am say hello world")
        self.assertEqual(p.get_message(), "hello world")
        
        p = SlashCommandParser("September 2nd, at 6:00, say 'Hello, world!'")
        self.assertEqual(p.get_message(), "Hello, world!")
        
        p = SlashCommandParser("1 hour say What did Sally say yesterday?")
        self.assertEqual(p.get_message(), "What did Sally say yesterday?")
        
        p = SlashCommandParser("1 hour say: I did say that.")
        self.assertEqual(p.get_message(), "I did say that.")
        
        p = SlashCommandParser("1 hour say ... ??? ...")
        self.assertEqual(p.get_message(), "... ??? ...")

if __name__ == '__main__':
    unittest.main()
