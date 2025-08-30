import argparse

from aiohttp import web

from mproxy.router import setup_routers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=12345, help="Port to listen on")
    args = parser.parse_args()

    app = web.Application()
    setup_routers(app)
    web.run_app(app, host="localhost", port=args.port)


if __name__ == "__main__":
    main()
