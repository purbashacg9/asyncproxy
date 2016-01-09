import logging
from datetime import datetime

import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.web
from tornado.httputil import ResponseStartLine

from handlers.statshandler import StatsHandler
from processrange.byte_range import RangeOperations
from utils import util

# global variables
g_stats_handler = StatsHandler(datetime.now())

class MainHandler(tornado.web.RequestHandler):

    def initialize(self, request_timeout):
        # dictionary of hash(source ip, resource) to request handler
        self.incoming_conns = {}

        self.range_list = None

        # content cache for media requests only.
        self.resource_cache = {}

        # cache for partial content
        self.resource_partial_cache = {}

        self.http_client = tornado.httpclient.AsyncHTTPClient()

        self.request_timeout = request_timeout

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
                return False
        elif range_in_query:
            requested_range = range_in_query

        logging.info("Received range  %s for uri %s " % (requested_range, self.request.path))
        if requested_range:
            logging.info("Adding to range list %s" % requested_range)
            self.range_list = RangeOperations.create_range(requested_range)
            for range in self.range_list:
                logging.info("Range added to list with start %s end %s" % (range[0], range[1]))
        return True

    @tornado.gen.coroutine
    def get(self, tail):
        if tail == '/stats':
            allstats = {}
            allstats["Start Time"] = g_stats_handler.get_start_time()
            allstats["Up Time"] = g_stats_handler.get_up_time()
            allstats["Bytes Transmitted (MB)"] = g_stats_handler.get_bytes_transmitted()
            allstats["Number of Get Requests Handled"] = g_stats_handler.requests_handled()

            self.render("templates/stats.html", stats=allstats, counters = g_stats_handler.get_counters())
            return

        g_stats_handler.set_requests_handled()
        hash_key = self.get_hash_params(self.request)

        # save the instance of the application handler that is handing this request.
        if hash_key not in self.incoming_conns:
            self.incoming_conns[hash_key] = self.request.connection
            logging.info("save connection  object against key %s" % hash_key)

        if not (self.check_for_range_params()):
            self.send_error(416, message="Range not satisfiable")
            self.finish()
            return

        response = yield self.send_request_to_origin(self.request)

        logging.info('got response with code %s' % response.code)
        path = self.request.path
        remote_ip = self.request.remote_ip

        hash_key = self.get_hash_params(response.request, path, remote_ip)
        if hash_key not in self.incoming_conns:
            logging.error("No incoming connection exists for remote_ip %s and path %s" %(remote_ip, path))
            #TODO REturn error from here? How?
        else:
            in_conn = self.incoming_conns[hash_key]
            logging.info("Found HTTPConnection object for remote_ip %s and path %s" %(remote_ip, path))

        g_stats_handler.set_response_type_counter(str(response.code))

        if response.code in [200, 304, 206]:
            content_length = response.headers.get('Content-Length', None)
            accept_ranges = response.headers.get('Accept-Ranges', None)
            logging.info("Origin server at %s returned response code %s " % (path, response.code))
            logging.info("Got content_length %s with accept_ranges %s" % (content_length, accept_ranges))
            g_stats_handler.set_bytes_transmitted(content_length)

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
                          (path, response.code, response.error.message))
            start_line = ResponseStartLine("HTTP/1.1", str(response.code), response.error.message)
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

        out_req.request_timeout = self.request_timeout
        response = yield self.http_client.fetch(out_req, raise_error=False)
        raise tornado.gen.Return(response)

        #self.download_resource(path)
        #except Exception as e:
        #    print "EXCEPTION", e
        #    logging.error("Error in Fetching URL %s" % (self.request.path))
        #    pass
