from tornado.httpclient import AsyncHTTPClient
import os
import os.path
import logging
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.escape
from tornado.concurrent import Future
from tornado import gen
from tornado.options import options, define, parse_config_file

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")

class MainHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.req_id = 0
        # dictionary of requested URI mapping to request handler instance
        self.req_uri = {}

    @tornado.gen.coroutine
    def prepare(self):
        self.req_id += 1
        #self.req_uri[self.req_id] = ""

    @tornado.gen.coroutine
    def get(self, tail):
        request_headers = self.request.headers

        range = self.get_query_argument("range")
        path = self.request.path
        # save the instance of the application handler that is handing this request.
        self.req_uri[path] = self

        ext = path.split(".")[1]
        if ext in ["mp4", "mpeg", "mov", "mp3", "pdf", "doc", "docx"]:
            self.send_request_to_origin(path)
        else:
            try:
                http = tornado.httpclient.AsyncHTTPClient()
                response = yield http.fetch(path)

                # retrieve the handler that was handling the request for the path and write back on the same response
                # so it returns to the same user agent which made the request.
                req_handler = self.req_uri.get(response.request.url)
                req_handler.write(response.body)
                req_handler.finish()
            except Exception as err:
                logging.error("Error in Fetching URL %s" % path)

    @tornado.gen.coroutine
    def send_request_to_origin(self, path):
        http = tornado.httpclient.AsyncHTTPClient()
        response = yield http.fetch(path)

        




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