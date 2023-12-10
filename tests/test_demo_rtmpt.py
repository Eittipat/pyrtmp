import asyncio
import os
import tempfile
import unittest

from example.demo_rtmpt import serve_rtmpt
from tests import invoke_command, remove_if_exist


class TestRTMP(unittest.IsolatedAsyncioTestCase):

    async def test_single_rtmpt(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            filename = "SampleVideo_1280x720_5mb.flv"
            stream_path = "rtmpt://127.0.0.1:5000/test/test_rtmpt"
            target = os.path.join(tempdir, "test_rtmpt" + ".flv")
            remove_if_exist(target)
            task0 = asyncio.create_task(serve_rtmpt(tempdir))

            # wait for server to start
            await asyncio.sleep(3)

            task1 = invoke_command(f"ffmpeg -i {filename} -c:v copy -c:a copy -f flv {stream_path}")

            # when
            await task1

            # then
            task0.cancel()
            while not task0.cancelled():
                await asyncio.sleep(1)

            # check flv
            stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
            self.assertEqual(stdout.decode().startswith("duration=26"), True)

    async def test_multiple_rtmpt(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            task0 = asyncio.create_task(serve_rtmpt(tempdir))

            # wait for server to start
            await asyncio.sleep(3)

            tasks = []
            for i in range(3):
                command = "ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv {}"
                stream_name = f"test_rtmpt_{i}"
                target = os.path.join(tempdir, stream_name + ".flv")
                remove_if_exist(target)
                tasks.append(invoke_command(command.format(f"rtmpt://127.0.0.1:5000/test/{stream_name}")))

            # when
            await asyncio.gather(*tasks)

            # then
            task0.cancel()
            while not task0.cancelled():
                await asyncio.sleep(1)

            # check flv
            for i in range(3):
                stream_name = f"test_rtmpt_{i}"
                target = os.path.join(tempdir, stream_name + ".flv")
                stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
                self.assertEqual(stdout.decode().startswith("duration=26"), True)
