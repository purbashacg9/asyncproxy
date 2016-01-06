import unittest
import sys
import logging
from src.processrange.byte_range import RangeOperations

SINGLE_BYTE_RANGE = "bytes=656708-656999"
SINGLE_SUFFIX_BYTE_RANGE = "bytes=-1"
SINGLE_PREFIX_BYTE_RANGE = "bytes=1000-"
MULTIPLE_BYTE_RANGE = "bytes=1000-2000,2001-4000,4001-5000"

class TestByteRange(unittest.TestCase):

    def test_byte_range_creation(self):
        logging.info("Testing byte range creation for : %s" % SINGLE_BYTE_RANGE)
        created_range = RangeOperations.create_range(SINGLE_BYTE_RANGE)
        self.assertEqual(created_range,[(656708,656999)],"Failed to create single byte range")

        logging.info("Testing byte range creation for : %s" % SINGLE_SUFFIX_BYTE_RANGE)
        created_range = RangeOperations.create_range(SINGLE_SUFFIX_BYTE_RANGE)
        self.assertEqual(created_range,[(0,-1)], "Failed to create single suffix byte range")

        logging.info("Testing byte range creation for : %s" % SINGLE_PREFIX_BYTE_RANGE)
        created_range = RangeOperations.create_range(SINGLE_PREFIX_BYTE_RANGE)
        self.assertEqual(created_range,[(1000,sys.maxsize)], "Failed to create single prefix byte range")

        logging.info("Testing byte range creation for : %s" % MULTIPLE_BYTE_RANGE)
        created_range = RangeOperations.create_range(MULTIPLE_BYTE_RANGE)
        self.assertEqual(created_range,[(1000,2000),(2001,4000), (4001, 5000)], "Failed to create multiple byte ranges")

    def test_get_range(self):
        get_range = RangeOperations.get_range_spec([(100,200)])
        self.assertEqual(get_range, "bytes=100-200",
                         "Incorrect byte range spec \'%s\' returned from get_range_spec" % get_range)

        get_range = RangeOperations.get_range_spec([(100,200),(201,400)])
        self.assertEqual(get_range, "bytes=100-200,201-400",
                         "Incorrect byte range spec \'%s\' returned from get_range_spec" % get_range)




if __name__ == '__main__':
    unittest.main()