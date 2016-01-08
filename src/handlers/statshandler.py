import logging
from datetime import datetime
from datetime import timedelta
import time

class StatsHandler(object):
    def __init__(self, start):
        """

        :param start: time when this object is initialised, which is basically when the MainHAndler starts
        :return: None
        """
        # start time stored as  timestamp
        self.start_time = time.mktime(start.timetuple())
        # running sum of content length transmitting received from origin server
        self.bytes_transmitted = 0
        self.range_requests_handled = 0
        self.counters = {"404": 0,
                         "200": 0,
                         "206": 0,
                         "416": 0,
                         "500": 0
                         }
        self.get_requests_handled = 0

    def get_start_time(self):
        """return start time in UTC"""
        return datetime.fromtimestamp(self.start_time)

    def get_up_time(self):
        """return total up time as a string of the form Hours:1, Minutes:44, Seconds:30"""
        current_time = datetime.now()
        # str of timedelta returns a string [D day[s], ][H]H:MM:SS[.UUUUUU]
        uptime = str(current_time - self.get_start_time())
        l1 = uptime.split(",")
        if len(l1) > 1:
            days = l1[0]
            hhmmss = l1[1].split(":")
        else:
            days = ""
            hhmmss = l1[0].split(":")

        uptime_string = "Uptime is {0} {1} Hours and {2} Minutes".format(days, hhmmss[0], hhmmss[1])
        return uptime_string

    def set_bytes_transmitted(self, bytes_count):
        self.bytes_transmitted += int(bytes_count)

    def set_requests_handled(self, count = 1):
        """
        Captures number of get requests received
        :param count: represents count of incoming get requests
        :return: None
        """
        self.get_requests_handled += count

    def set_response_type_counter(self, response_code):
        """
        :param response_code: HTTP response code
        :return: None
        """
        counter = self.counters.get(response_code, None)
        if counter:
            self.counters[response_code] += 1
        else:
            # response code not found in counter dict
            pass

