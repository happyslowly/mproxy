from aiohttp import web

from mproxy.router import setup_routers

if __name__ == "__main__":
    app = web.Application()

    setup_routers(app)
    web.run_app(app, host="localhost", port=12345)
