import asyncio
import os
import tempfile
import unittest

from example.demo_flvdump import serve_rtmp
from tests import invoke_command, remove_if_exist


class TestFLVDump(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        _loop = asyncio.get_event_loop()
        _loop._close_loop = _loop.close
        _loop.close = lambda: ()
        asyncio.set_event_loop(_loop)

    async def test_single_rtmp(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            command = "ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv {}"
            stream_name = "test_rtmp"
            target = os.path.join(tempdir, stream_name + ".flv")
            remove_if_exist(target)
            task0 = asyncio.create_task(serve_rtmp(tempdir))

            # wait for server to start
            await asyncio.sleep(3)

            task1 = invoke_command(command.format(f"rtmp://127.0.0.1:1935/test/{stream_name}"))

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
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            task0 = asyncio.create_task(serve_rtmp(tempdir))

            # wait for server to start
            await asyncio.sleep(3)

            tasks = []
            for i in range(3):
                command = "ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv {}"
                stream_name = f"test_rtmp_{i}"
                target = os.path.join(tempdir, stream_name + ".flv")
                remove_if_exist(target)
                tasks.append(invoke_command(command.format(f"rtmp://127.0.0.1:1935/test/{stream_name}")))

            # when
            await asyncio.gather(*tasks)

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
