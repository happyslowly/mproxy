import asyncio
from typing import Callable

import aiohttp
from loguru import logger

from mproxy.config import config
from mproxy.utils import find_free_port, resolve_huggingface


class LlamaCppManager:
    def __init__(self):
        self._processes = {}

    def _is_running(self, name):
        return name in self._processes

    @property
    def processes(self):
        return self._processes

    async def get_process(self, name) -> dict | None:
        if not name in self._processes:
            await self.swap(
                name,
                output_callback=lambda l: logger.info(l),
                error_callback=lambda l: logger.info(l),
            )
        return self._processes.get(name)

    async def start(
        self,
        name: str,
        output_callback: Callable | None = None,
        error_callback: Callable | None = None,
    ):
        if not self._is_running(name) and name in config.get("models", {}):
            await self._run(name, output_callback, error_callback)

    async def swap(
        self,
        name: str,
        output_callback: Callable | None = None,
        error_callback: Callable | None = None,
    ):

        if not self._is_running(name) and name in config.get("models", {}):
            await self.stop_all()
            await self._run(name, output_callback, error_callback)

    async def _run(
        self,
        name: str,
        output_callback: Callable | None = None,
        error_callback: Callable | None = None,
    ):
        if self._is_running(name):
            return

        model_config = config["models"].get(name)
        if not model_config or "repo" not in model_config or "args" not in model_config:
            raise ValueError(f"Model `{name}` is not configured properly")
        port = find_free_port()
        command = self._build_llamacpp_command(
            model_config["repo"],
            model_config["args"],
            port,
            model_filename=config.get("model_file"),
        )
        logger.info(f"Starting process {name}: {' '.join(command)}...")
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._processes[name] = {"process": process, "tasks": [], "port": port}
        if output_callback:
            task = asyncio.create_task(
                self._handle_stream(process.stdout, output_callback)
            )
            self._processes[name]["tasks"].append(task)

        if error_callback:
            task = asyncio.create_task(
                self._handle_stream(process.stderr, error_callback)
            )
            self._processes[name]["tasks"].append(task)

        pid = process.pid
        logger.info(f"Process `{name}` started with PID: `{pid}`")
        await self._wait_for_server(port)
        self._processes[name]["pid"] = pid
        logger.info(f"Process `{name}` is ready on port {port}")

    async def _handle_stream(self, stream, callback: Callable):
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded_line = line.decode().strip()
                if decoded_line:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(decoded_line)
                    else:
                        callback(decoded_line)
        except Exception as e:
            logger.error(f"Error handling stream: {e}")

    async def _wait_for_server(self, port: int, timeout: int = 30):
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{port}/health",
                        timeout=aiohttp.ClientTimeout(total=1),
                    ) as resp:
                        if resp.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Server on port {port} failed to start within {timeout}s")

    async def stop_all(self, keep_persist: bool = True):
        for name in list(self._processes.keys()):
            persist = config.get("models", {}).get(name, {}).get("persist", False)
            if keep_persist and persist:
                continue
            await self.stop(name)

    async def stop(self, name: str, timeout: int = 5, force: bool = False):
        if name not in self._processes:
            logger.warning(f"Process `{name}` not found")
            return
        process_info = self._processes[name]
        process = process_info["process"]
        try:
            for task in process_info["tasks"]:
                task.cancel()
            if process_info["tasks"]:
                await asyncio.gather(*process_info["tasks"], return_exceptions=True)

            if force:
                process.kill()
            else:
                process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.info(f"Process `{name}` didn't terminate, force killing...")
                process.kill()
                await process.wait()

            del self._processes[name]
            logger.info(f"Process `{name}` terminated")
        except Exception as e:
            logger.error(f"Error stopping process `{name}`: {e}")

    def _build_llamacpp_command(
        self, repo: str, args: dict, port: int, model_filename: str | None = None
    ) -> list[str]:
        command = ["llama-server"]
        command.append("-m")
        command.append(str(resolve_huggingface(repo, model_filename).absolute()))

        command.append("--port")
        command.append(str(port))

        for k, v in args.items():
            if v is True:
                command.append(k)
            elif v == False:
                continue
            else:
                command.append(k)
                command.append(str(v))

        return command
