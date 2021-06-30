import asyncio
import os
import tempfile

import psutil as psutil
from aiounittest import AsyncTestCase

from pyrtmp.misc.rtmpt import serve_rtmpt
from pyrtmp.rtmp import serve_rtmp


async def invoke_command(command: str):
    try:
        proc = await asyncio.subprocess.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode > 0:
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


class TestRTMP(AsyncTestCase):

    async def test_single_rtmp(self):
        # given
        stream_name = "test_rtmp"
        target = os.path.join(tempfile.gettempdir(), stream_name)
        if os.path.exists(target):
            os.remove(target)
        task0 = asyncio.create_task(serve_rtmp())
        task1 = invoke_command(f"ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv rtmp://127.0.0.1:1935/test/{stream_name}")

        # when
        await task1

        # then
        task0.cancel()
        while not task0.cancelled():
            await asyncio.sleep(1)

        # check flv
        stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
        self.assertEqual(stdout.decode().startswith("duration=26"), True)

    async def test_multiple_rtmp(self):
        # given
        task0 = asyncio.create_task(serve_rtmp())
        tasks = []
        for i in range(3):
            stream_name = f"test_rtmp_{i}"
            target = os.path.join(tempfile.gettempdir(), stream_name)
            if os.path.exists(target):
                os.remove(target)
            tasks.append(invoke_command(f"ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv rtmp://127.0.0.1:1935/test/{stream_name}"))

        # when
        await asyncio.wait(tasks)

        # then
        task0.cancel()
        while not task0.cancelled():
            await asyncio.sleep(1)

        # check flv
        for i in range(3):
            stream_name = f"test_rtmp_{i}"
            target = os.path.join(tempfile.gettempdir(), stream_name)
            stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
            self.assertEqual(stdout.decode().startswith("duration=26"), True)

    async def test_rtmpt(self):
        # given
        stream_name = "test_rtmpt"
        target = os.path.join(tempfile.gettempdir(), stream_name)
        if os.path.exists(target):
            os.remove(target)
        task0 = asyncio.create_task(serve_rtmpt())
        task1 = invoke_command(f"ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv rtmpt://127.0.0.1:5000/test/{stream_name}")

        # when
        await task1

        # then
        task0.cancel()
        while not task0.cancelled():
            await asyncio.sleep(1)

        # check flv
        stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
        self.assertEqual(stdout.decode().startswith("duration=26"), True)
