import logging

import tornado.escape
import tornado.gen
import tornado.ioloop
import tornado.web
from tornado.httputil import ResponseStartLine
from tornado.options import options, define, parse_config_file

import util
from src.processrange.byte_range import RangeOperations

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")


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
        requested_range = self.request.headers.get("Range", None)

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

        if response.code in [200, 304, 206]:
            content_length = response.headers.get('Content-Length', None)
            accept_ranges = response.headers.get('Accept-Ranges', None)
            logging.info("Origin server at %s returned response code %s " % (path, response.code))
            logging.info("Got content_length %s with accept_ranges %s" % (content_length, accept_ranges))

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
        if self.range_list is None or self.range_list:
            out_req = tornado.httpclient.HTTPRequest(path, method="GET")
            for item, value in request.headers.iteritems():
                out_req.headers[item] = value
            out_req.request_timeout = 60
            response = yield self.http_client.fetch(out_req, raise_error=False)
            raise tornado.gen.Return(response)
        else:
            self.download_resource(path)
        #except Exception as e:
        #    print "EXCEPTION", e
        #    logging.error("Error in Fetching URL %s" % (self.request.path))
        #    pass



def main():
    parse_config_file("/home/purbasha/Projects/learntornado/settings.conf")

    app = tornado.web.Application(
        [
            (r"(.*)", MainHandler),
       ],
        debug=options.debug,
        )
    app.listen(options.port)
    logging.info("Listening on port %s" % options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()