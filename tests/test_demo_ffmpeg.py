import asyncio
import os
import tempfile

from aiounittest import AsyncTestCase
from example.demo_ffmpeg import serve_rtmp
from tests import invoke_command, remove_if_exist


class TestFFMPEG(AsyncTestCase):

    async def test_single_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            stream_name = "test_ffmpeg"
            command = "ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv {}"
            target = os.path.join(tempdir, stream_name + ".flv")
            remove_if_exist(target)

            task0 = asyncio.create_task(serve_rtmp(tempdir))
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

    async def test_multiple_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # given
            task0 = asyncio.create_task(serve_rtmp(tempdir))
            tasks = []
            for i in range(3):
                stream_name = f"test_ffmpeg_{i}"
                command = "ffmpeg -i SampleVideo_1280x720_5mb.flv -c:v copy -c:a copy -f flv {}"
                target = os.path.join(tempdir, stream_name + ".flv")
                remove_if_exist(target)
                tasks.append(invoke_command(command.format(f"rtmp://127.0.0.1:1935/test/{stream_name}")))

            # when
            await asyncio.wait(tasks)

            # then
            task0.cancel()
            while not task0.cancelled():
                await asyncio.sleep(1)

            # check flv
            for i in range(3):
                stream_name = f"test_ffmpeg_{i}"
                target = os.path.join(tempdir, stream_name + ".flv")
                stdout, stderr = await invoke_command(f"ffprobe -i {target} -show_format | grep duration")
                self.assertEqual(stdout.decode().startswith("duration=26"), True)
