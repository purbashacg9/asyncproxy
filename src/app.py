import logging
from datetime import datetime
from datetime import timedelta
import time

import tornado.escape
import tornado.gen
import tornado.ioloop
import tornado.web
import tornado.httpclient
from tornado.httputil import ResponseStartLine
from tornado.options import options, define, parse_config_file

import util
from src.processrange.byte_range import RangeOperations

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")
define("request_timeout", default=30, help="timeout for incoming requests", type=int)

class StatsManager(object):
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


class MainHandler(tornado.web.RequestHandler):

    def initialize(self):
        # dictionary of hash(source ip, resource) to request handler
        self.incoming_conns = {}

        self.range_list = None

        # content cache for media requests only.
        self.resource_cache = {}

        # cache for partial content
        self.resource_partial_cache = {}

        self.http_client = tornado.httpclient.AsyncHTTPClient()

        self.stats_manager = StatsManager(datetime.now())

    def get_hash_params(self, request, path=None,  remote_ip=None):
        #print repr(request)

        if not remote_ip:
            x_real_ip = request.headers.get("X-Real-IP")
            if not hasattr(request, "remote_ip"):
                request.remote_ip = ""
            remote_ip = x_real_ip or request.remote_ip
        if path:
            resource = path.split("/")[-1]
        else:
            resource = request.path.split("/")[-1]

        # Create a hash key for resource dict with remote ip and resource name
        hash_key = util.make_key(remote_ip, resource)
        logging.info("hash key %s created for ip %s and resource %s" %(hash_key, remote_ip, resource))
        return hash_key

    def check_for_range_params(self):
        range_in_query = self.get_query_argument("range", None)
        if not range_in_query:
            range_in_query = self.get_query_argument("Range", None)
        logging.info("Range %s received as query param " % range_in_query)

        requested_range = self.request.headers.get("Range", None)
        logging.info("Range %s received as request header " % requested_range)

        if range_in_query and requested_range:
            if range_in_query != requested_range:
                logging.error("Mismatch in ranges -> Range in header %s, rang in query param %s" %
                                                    (requested_range, range_in_query))
                self.send_error("416", "Incorrect range parameters")
                self.finish()
        elif range_in_query:
            requested_range = range_in_query

        logging.info("Received range  %s for uri %s " % (requested_range, self.request.path))
        if requested_range:
            logging.info("Adding to range list %s" % requested_range)
            self.range_list = RangeOperations.create_range(requested_range)
            for range in self.range_list:
                logging.info("Range added to list with start %s end %s" % (range[0], range[1]))


    @tornado.gen.coroutine
    def get(self, tail):
        self.stats_manager.set_requests_handled()
        hash_key = self.get_hash_params(self.request)

        # save the instance of the application handler that is handing this request.
        if hash_key not in self.incoming_conns:
            self.incoming_conns[hash_key] = self.request.connection
            logging.info("save connection  object against key %s" % hash_key)

        # resource = self.request.path.split("/")[-1]
        # ext = resource.split(".")[-1]
        self.check_for_range_params()
        response = yield self.send_request_to_origin(self.request)

        logging.info('got response with code %s' % response.code)
        path = self.request.path
        remote_ip = self.request.remote_ip
        #TODO - when response is received for remote what should hash_key resolve?
        hash_key = self.get_hash_params(response.request, path, remote_ip)
        if hash_key not in self.incoming_conns:
            logging.error("No incoming connection exists for remote_ip %s and path %s" %(remote_ip, path))
            #TODO REturn error from here? How?
        else:
            in_conn = self.incoming_conns[hash_key]
            logging.info("Found HTTPConnection object for remote_ip %s and path %s" %(remote_ip, path))

        self.stats_manager.set_response_type_counter(response.code)

        if response.code in [200, 304, 206]:
            content_length = response.headers.get('Content-Length', None)
            accept_ranges = response.headers.get('Accept-Ranges', None)
            logging.info("Origin server at %s returned response code %s " % (path, response.code))
            logging.info("Got content_length %s with accept_ranges %s" % (content_length, accept_ranges))
            self.stats_manager.set_bytes_transmitted(content_length)

            if response.code == 206:
                logging.info("Received Content-Range %s for Content-Type %s " %
                             (response.headers.get('Content-Range', None), response.headers.get('Content-Type', None)))

            resource = self.request.path.split("/")[-1]
            resource_details = self.resource_cache.get(resource, None)
            if resource_details is None:
                self.resource_cache[resource] = {"path": path, "content-length": content_length}

            # send accept ranges back to the client
            start_line = ResponseStartLine("HTTP/1.1", str(response.code), response.reason)
            in_conn.write_headers(start_line, response.headers)
            in_conn.write(response.body)
        elif response.code == 416:
            logging.info("Origin server at %s returned response code %s " % (path, response.code))
            start_line = ResponseStartLine("HTTP/1.1", str(response.code), response.error.message)
            in_conn.write_headers(start_line, response.headers)
        else:
            logging.error("Origin server at %s returned error code %s with message %s" %
                          (path, response.error.code, response.error.message))
            start_line = ResponseStartLine("HTTP/1.1", str(response.error.code), response.error.message)
            in_conn.write_headers(start_line, response.headers)

        in_conn.finish()



    @tornado.gen.coroutine
    def send_request_to_origin(self, request):
        path = request.path
        remote_ip = request.remote_ip
        logging.info("Get resource %s" % path)
        #try:

        out_req = tornado.httpclient.HTTPRequest(path, method="GET")
        for item, value in request.headers.iteritems():
            out_req.headers[item] = value

        # If there are items in range list, copy them into headers field.
        # This takes care of sending range requests sent by client as query param
        if  self.range_list:
            out_req.headers.add("Range", RangeOperations.get_range_spec(self.range_list))

        out_req.request_timeout = options.request_timeout
        response = yield self.http_client.fetch(out_req, raise_error=False)
        raise tornado.gen.Return(response)

        #self.download_resource(path)
        #except Exception as e:
        #    print "EXCEPTION", e
        #    logging.error("Error in Fetching URL %s" % (self.request.path))
        #    pass

class StatsHandler(tornado.web.RequestHandler):
    """Render html page showing Proxy Stats"""
    pass


def main():
    parse_config_file("/home/purbasha/Projects/learntornado/settings.conf")

    app = tornado.web.Application(
        [
            (r"(.*)", MainHandler),
            (r"/stats", StatsHandler)
       ],
        debug=options.debug,
        )
    app.listen(options.port)
    logging.info("Listening on port %s" % options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()