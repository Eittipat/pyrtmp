# PyRTMP: Pure Python RTMP server
![coverage](https://github.com/Eittipat/pyrtmp/blob/master/coverage.svg)
## Features

- ✅ Pure Python
- ✅ Easy to customize
- ✅ Production Ready
- ✅ UV loop
- ✅ PyPy
- ✅ Support RTMP(s)
- ✅ Support RTMPT(s)

## Announcement

After using this package for years in production server. It runs flawlessly without any problem.
So I decided to switch the development status from **Beta** to **Production** since version 0.2.0. Also,
I share my configuration at Deployment section below.

If you have any problems. Feel free to create issue on [GitHub](https://github.com/Eittipat/pyrtmp/issues).

## What's new

### 0.3.0

- Clean up, refactoring, bug fixes
- Add more testcases.
- Add support to Python 3.11
- Add GitHub action workflows
- Add [RTMP to FFMPEG](https://github.com/Eittipat/pyrtmp/blob/master/example/demo_ffmpeg.py) example
- Add [RTMP to FLV](https://github.com/Eittipat/pyrtmp/blob/master/example/demo_flvdump.py) example
- Add [RTMPT](https://github.com/Eittipat/pyrtmp/blob/master/example/demo_rtmpt.py) example

## Installation

Install from PyPI:
```
pip install pyrtmp
```
Install from source:
```
pip install pyrtmp@git+https://github.com/Eittipat/pyrtmp.git
```

## Quickstart

Let say we want to create a simple RTMP server that can save all incoming stream to FLV file.
We can do it by creating a subclass of [*Simple RTMP
controller*](https://github.com/Eittipat/pyrtmp/blob/master/pyrtmp/rtmp.py)
and override some methods.
Here is the example:

```python
import asyncio
import os
import logging

from pyrtmp import StreamClosedException
from pyrtmp.flv import FLVFileWriter, FLVMediaType
from pyrtmp.session_manager import SessionManager
from pyrtmp.rtmp import SimpleRTMPController, RTMPProtocol, SimpleRTMPServer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RTMP2FLVController(SimpleRTMPController):

    def __init__(self, output_directory: str):
        self.output_directory = output_directory
        super().__init__()

    async def on_ns_publish(self, session, message) -> None:
        publishing_name = message.publishing_name
        file_path = os.path.join(self.output_directory, f"{publishing_name}.flv")
        session.state = FLVFileWriter(output=file_path)
        await super().on_ns_publish(session, message)

    async def on_metadata(self, session, message) -> None:
        session.state.write(0, message.to_raw_meta(), FLVMediaType.OBJECT)
        await super().on_metadata(session, message)

    async def on_video_message(self, session, message) -> None:
        session.state.write(message.timestamp, message.payload, FLVMediaType.VIDEO)
        await super().on_video_message(session, message)

    async def on_audio_message(self, session, message) -> None:
        session.state.write(message.timestamp, message.payload, FLVMediaType.AUDIO)
        await super().on_audio_message(session, message)

    async def on_stream_closed(self, session: SessionManager, exception: StreamClosedException) -> None:
        session.state.close()
        await super().on_stream_closed(session, exception)


class SimpleServer(SimpleRTMPServer):

    def __init__(self, output_directory: str):
        self.output_directory = output_directory
        super().__init__()

    async def create(self, host: str, port: int):
        loop = asyncio.get_event_loop()
        self.server = await loop.create_server(
            lambda: RTMPProtocol(controller=RTMP2FLVController(self.output_directory)),
            host=host,
            port=port,
        )


async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server = SimpleServer(output_directory=current_dir)
    await server.create(host='0.0.0.0', port=1935)
    await server.start()
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
```

Next, we can test our server by executing the following command:

```
ffmpeg -i my_test_file.flv -c:v copy -c:a copy -f flv rtmp://127.0.0.1:1935/test/sample
```

Your flv file will be saved in the same directory as your python script.

## Deployment

In production environment, You should run multiple instances of RTMP server and use load balancer to distribute incoming
stream.
I recommend to use `Nginx` as a load balancer and `Supervisord` to manage your RTMP server instances.
Also, `uvloop` or `pypy` can be used to boost your performance.

Here is nginx configuration example:

```
stream {

    upstream stream_backend {
        127.0.0.1:1936;
        127.0.0.1:1937;
    }

    server {
        listen     1935;
        proxy_pass stream_backend;
    }
}
```

## Benchmark

Coming soon.

## Roadmap

- Support AMF3
- ReStream / Client Mode
- Documentation

