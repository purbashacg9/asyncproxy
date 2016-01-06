import logging
import sys


class RangeOperations:
    @staticmethod
    def create_range(str_range):
        """Given a byte range specifier as a string, create a byte range tuple with start pos and end pos.
        If there are multiple byte ranges, create a list of byte range tuples.
        If str_range is valid, returns a list with one or more tuples containing byte ranges, else returns None
        """
        byte_ranges = None

        # Look for "bytes" as range unit
        range_string = str_range.split("=")
        if range_string[0] != "bytes":
            return None

        # Parse range string to form the list of tuples containing start and end pos
        ranges = range_string[1].split(",")
        byte_ranges = [tuple(r.split("-")) for r in ranges]

        byte_ranges = RangeOperations.validate_range(byte_ranges)

        return byte_ranges


    @staticmethod
    def validate_range(range_list):
        """Given a list of byte range tuples, do the following -
        - sort the tuples by start value in ascending order
        - if a tuple has blank start pos, store start pos as 0.
        - if a tuple has blank end pos, store end pos as 0.
        - if in a tuple end pos < start pos, remove it from range list
        - check that end pos in tuple (n-1) is < start pos of tuple n - TODO
        Last one can be implemented to take care of combining byte ranges
        """
        numeric_byte_ranges = []

        for byte_range in range_list:
            start_pos = long(byte_range[0]) if len(byte_range[0]) else 0
            end_pos = long(byte_range[1]) if len(byte_range[1]) else 0
            numeric_byte_ranges.append((start_pos, end_pos))

        # sorted byte range list
        srt_byte_ranges = sorted(numeric_byte_ranges)

        numeric_byte_ranges = []
        ind = 0
        while ind < len(srt_byte_ranges):
            # for non zero start and end pos, end pos should be greater than start pos
            if srt_byte_ranges[ind][1] and srt_byte_ranges[ind][0]:
                if srt_byte_ranges[ind][1] > srt_byte_ranges[ind][0]:
                    # copy valid ranges back to numeric_byte_ranges
                    numeric_byte_ranges.append(srt_byte_ranges[ind])
                else:
                    logging.info("end pos less than start pos in byte range %s-%s " %
                                 (srt_byte_ranges[ind][0], srt_byte_ranges[ind][1]))
            elif srt_byte_ranges[ind][0]:
                numeric_byte_ranges.append((srt_byte_ranges[ind][0],sys.maxsize))
            else:
                numeric_byte_ranges.append((0, -srt_byte_ranges[ind][1]))

            ind += 1

        return numeric_byte_ranges


    @staticmethod
    def intepret_range(start, end):
        pass