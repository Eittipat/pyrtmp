import asyncio
import logging
import os

import psutil as psutil


def remove_if_exist(path: str):
    if os.path.exists(path):
        os.remove(path)


async def invoke_command(command: str):
    proc = None
    try:
        proc = await asyncio.subprocess.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode > 0:
            logging.exception(stderr.decode())
            raise Exception("Non-zero returned")

        return stdout, stderr
    finally:
        if proc and proc.returncode is None:
            process = psutil.Process(proc.pid)
            to_be_kill = [p for p in process.children(recursive=True)]
            to_be_kill.append(process)
            exception = None
            for p in to_be_kill:
                try:
                    p.kill()
                except Exception as ex:
                    exception = ex
            if exception:
                raise exception
