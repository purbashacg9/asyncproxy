
import os
import os.path

import logging

from tornado.httpclient import AsyncHTTPClient
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.escape
from tornado.options import options, define, parse_config_file

from byte_range import RangeOperations
import util

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")


class MainHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.req_id = 0
        # dictionary of hash(source ip, resource) to request handler
        self.request_handler = {}
        self.range_list = None

        # content cache for media requests only.
        self.resource_cache = {}

        # cache for partial content
        self.resource_partial_cache = {}

    @tornado.gen.coroutine
    def prepare(self):
        self.req_id += 1
        # self.req_uri[self.req_id] = ""


    def get_hash_params(self, request):
        x_real_ip = request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or request.remote_ip
        resource = request.path.split("/")[-1]
        # Create a hash key for resource dict with remote ip and resource name
        hash_key = util.make_key(remote_ip, resource)
        logging.info("hash key %s created for ip %s and uri %s" %(hash_key, remote_ip, request.path))
        return hash_key


    @tornado.gen.coroutine
    def get(self, tail):
        hash_key = self.get_hash_params(self.request)

        # save the instance of the application handler that is handing this request.
        if hash_key not in self.request_handler:
            self.request_handler[hash_key] = self
            logging.info("storing handler object against key %s" % hash_key)

        # If resource is video, audio, go into range request flow
        resource = self.request.path.split("/")[-1]
        ext = resource.split(".")[-1]
        if ext in ["mp4", "mpeg", "mov", "mp3", "pdf", "doc", "docx"]:
            #TODO - could also check content/type in header
            # handle range requests
            range_in_query = self.get_query_argument("range", None)
            if not range_in_query:
                range_in_query = self.get_query_argument("Range", None)
            requested_range = self.request.headers.get("Range", None)

            if range_in_query and requested_range:
                if range_in_query != requested_range:
                    self.send_error("416", "Incorrect range parameters")
                    self.finish()
            elif range_in_query:
                requested_range = range_in_query

            logging.info("Received range in get request  %s for uri %s " % (requested_range, self.request.path))
            if requested_range:
                self.range_list = RangeOperations.create_range(requested_range)

            self.send_request_to_origin(self.request.path)
        else:
            try:
                http = tornado.httpclient.AsyncHTTPClient()
                response = yield http.fetch(self.request.path)

                # retrieve the handler that was handling the request for the path and write back on the same response
                # so it returns to the same user agent which made the request.
                hash_key = self.get_hash_params(self.request)
                req_handler = self.request_handler[hash_key]
                req_handler.write(response.body)
                req_handler.finish()
            except Exception as err:
                logging.error("Error in Fetching URL %s, details %s" % (self.request.path, err.errorno))

    @tornado.gen.coroutine
    def send_request_to_origin(self, path):
        if self.range_list is None or self.range_list:
            http = tornado.httpclient.AsyncHTTPClient()
            response = yield http.fetch(path)

            hash_key = self.get_hash_params(self.request)
            req_handler = self.request_handler[hash_key]

            if response.code in [200, 304]:
                content_length = response.headers.get('Content-Length', None)
                accept_ranges = response.headers.get('Accept-Ranges', None)
                logging.info("Got content_length %s with accept_ranges %s" % (content_length, accept_ranbes))

                resource_details = self.resource_cache.get(resource, None)
                if resource_details is None:
                    self.resource_cache[resource] = {"path": path, "content-length": content_length}

                # send accept ranges back to the client
                req_handler.write(response.body)
                req_handler.finish()

                # if accept_ranges is not None:
                #     if accept_ranges == "bytes":
                #         # Send request with a Range Parameter
                #         resource_request = tornado.httpclient.HttpRequest()
                #         resource_request.url = path
                #         resource_request.method = "GET"
                #         resource_request.headers.add("Range", "0-%s" % content_length)
                #         response = yield http.fetch(resource_request)
                #
                #
                #     else:
                #         logging.info("Origin server at %s does not support bytes range" % path)
                # else:
                #     logging.info("Origin Server at %s does not support range requests " % path)
            elif response.code == "206":
                logging.info("Origin server at %s returned response code %s " % (path, response.code))
            elif response.code == "416":
                logging.info("Origin server at %s returned response code %s " % (path, response.code))
            else:
                logging.error("Origin server at %s returned error %s " % (path, response.error))
                req_handler.write_error(response.error)
                req_handler.finish()
        else:
            self.download_resource(path)


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