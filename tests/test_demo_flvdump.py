import asyncio
import os
import tempfile

from aiounittest import AsyncTestCase
from example.demo_flvdump import serve_rtmp
from tests import invoke_command


class TestFLVDump(AsyncTestCase):

    async def test_single_rtmp(self):
        # given
        stream_name = "test_rtmp"
        target = os.path.join(tempfile.gettempdir(), stream_name + ".flv")
        if os.path.exists(target):
            os.remove(target)
        task0 = asyncio.create_task(serve_rtmp(tempfile.gettempdir()))
        task1 = invoke_command(
            f"ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv rtmp://127.0.0.1:1935/test/{stream_name}")

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
        task0 = asyncio.create_task(serve_rtmp(tempfile.gettempdir()))
        tasks = []
        for i in range(3):
            stream_name = f"test_rtmp_{i}"
            target = os.path.join(tempfile.gettempdir(), stream_name + ".flv")
            if os.path.exists(target):
                os.remove(target)
            tasks.append(invoke_command(
                f"ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv rtmp://127.0.0.1:1935/test/{stream_name}"))

        # when
        await asyncio.wait(tasks)

        # then
        task0.cancel()
        while not task0.cancelled():
            await asyncio.sleep(1)

        # check flv
        for i in range(3):
            stream_name = f"test_rtmp_{i}"
            target = os.path.join(tempfile.gettempdir(), stream_name + ".flv")
            stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
            self.assertEqual(stdout.decode().startswith("duration=26"), True)
