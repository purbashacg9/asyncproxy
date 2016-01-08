import logging

import tornado.ioloop
from tornado.options import options, define, parse_config_file

from src.handlers.mainhandler import MainHandler
from src.handlers.statshandler import StatsHandler

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")
define("request_timeout", default=30, help="timeout for incoming requests", type=int)


def main():
    parse_config_file("/home/purbasha/Projects/learntornado/settings.conf")

    app = tornado.web.Application(
        [
            (r"(.*)", MainHandler, dict(request_timeout=options.request_timeout)),
            (r"/stats", StatsHandler)
       ],
        debug=options.debug,
        )
    app.listen(options.port)
    logging.info("Listening on port %s" % options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()