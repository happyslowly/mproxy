import asyncio
import json

import aiohttp
from aiohttp import web
from loguru import logger

from mproxy.config import config
from mproxy.llama import LlamaCppManager

llama_manager = LlamaCppManager()


async def _get_port(path: str, body_str: str) -> int:
    body = json.loads(body_str)
    if path.startswith("/v1"):
        name = body["model"]
        model_info = await llama_manager.get_process(name)
        if not model_info:
            raise ValueError(f"Model `{name}` not found")
        return model_info["port"]
    else:
        raise ValueError(f"`{path}` is not support yet")


async def proxy_handler(
    request: web.Request,
    target_host: str = "localhost",
    target_port: int = 8080,
    timeout: int = 30,
) -> web.Response | web.StreamResponse:
    try:
        body = await request.read()
        target_port = await _get_port(request.path, body.decode("utf-8"))
        target_url = f"http://{target_host}:{target_port}{request.path_qs}"
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)
    except FileNotFoundError as e:
        return web.json_response({"error": str(e)}, status=404)
    except Exception as e:
        return web.json_response({"error": f"Model startup failed: {e}"}, status=503)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                data=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                content_type = response.headers.get("Content-Type", "")
                is_streaming = (
                    "text/event-stream" in content_type
                    or response.headers.get("Transfer-Encoding") == "chunked"
                )
                logger.info(
                    f'{request.remote} "{request.method} {request.path_qs}" {response.status}'
                )
                if is_streaming:
                    return await stream_response(request, response)
                else:
                    response_body = await response.read()
                    return web.Response(
                        body=response_body,
                        status=response.status,
                        headers=response.headers,
                    )
        except aiohttp.ClientError as e:
            return web.json_response({"error": f"Proxy error: {e}"}, status=502)
        except asyncio.TimeoutError as _:
            return web.json_response({"error": "Request timeout"}, status=504)


async def stream_response(
    request: web.Request,
    backend_response: aiohttp.ClientResponse,
    chunk_size: int = 8192,
) -> web.StreamResponse:
    response = web.StreamResponse(
        status=backend_response.status, headers=backend_response.headers
    )
    await response.prepare(request)
    try:
        async for chunk in backend_response.content.iter_chunked(chunk_size):
            if chunk:
                await response.write(chunk)
        await response.write_eof()
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        await response.write_eof()
    return response


async def models_handler(request) -> web.Response:
    _ = request
    data = []
    for model in config["models"]:
        data.append({"id": model, "object": "model", "owned_by": "llamacpp"})

    return web.json_response({"object": "list", "data": data})


async def status_handler(request) -> web.Response:
    _ = request
    statuses = []
    for name, process in llama_manager.processes.items():
        statuses.append({"model": name, "port": process["port"], "pid": process["pid"]})
    return web.json_response(statuses)


async def unload_handler(request) -> web.Response:
    name = request.match_info["name"]
    await llama_manager.stop(name)
    return web.Response(status=204)


def setup_routers(app):
    # internal
    app.router.add_route("GET", "/models/running", status_handler)
    app.router.add_route("DELETE", "/models/{name}", unload_handler)

    # proxy
    app.router.add_route("GET", "/v1/models", models_handler)
    app.router.add_route("POST", "/{path:.*}", proxy_handler)
