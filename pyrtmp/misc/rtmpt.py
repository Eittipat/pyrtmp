import asyncio
import logging
import uuid
from asyncio import StreamReader, StreamWriter, events
from io import BytesIO

import quart
from bitstring import BitArray, BitStream

from pyrtmp import BufferedWriteTransport
from pyrtmp.rtmp import simple_controller

session = {}

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class RTMPWrapper:

    def __init__(self,
                 session_id: str,
                 peer: tuple,
                 controller,
                 loop: events.AbstractEventLoop) -> None:
        self.delay = 0
        self.loop = loop
        self.session_id = session_id
        self.peer = peer
        self.controller = controller
        self.stream = BytesIO()
        self.reader = StreamReader(loop=self.loop)
        self.writer = StreamWriter(
            BufferedWriteTransport(self.stream, extra={
                "peername": peer,
            }),
            asyncio.StreamReaderProtocol(self.reader, self.loop),
            self.reader,
            self.loop)
        self.task = self.loop.create_task(self._dispatcher())

    async def _dispatcher(self):
        try:
            await self.controller(self.reader, self.writer)
        except Exception as ex:
            logger.exception(ex)
            raise ex

    def _get_polling_delay(self):
        temp = self.delay
        self.delay = min(self.delay + 10, 255)
        return temp

    def close(self):
        assert len(self.stream.read()) == 0
        self.reader.feed_eof()
        self.writer.close()
        self.stream.close()

    async def read_from_buffer(self):
        data = BitStream()
        data.append(BitArray(uint=self._get_polling_delay(), length=8).bytes)
        while True:
            await asyncio.sleep(0)
            payload = await self.get_buffered_data()
            if len(payload) == 0:
                break
            data.append(payload)
            self.delay = 0
        return data.bytes

    async def get_buffered_data(self):
        self.stream.seek(0)
        buffer = self.stream.read()
        self.stream.truncate(0)
        return buffer


from quart import Quart, request

app = Quart(__name__)


@app.route('/open/<int:segment>', methods=['POST'])
async def open(segment: int):
    # body = await request.body
    # assert body == b'\x00'
    sid = uuid.uuid4().hex
    session[sid] = RTMPWrapper(
        session_id=sid,
        peer=request.scope["client"],
        controller=simple_controller,
        loop=asyncio.get_running_loop())
    resp = quart.Response(sid)
    resp.headers['Content-Type'] = 'application/x-fcs'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/send/<string:sid>/<int:segment>', methods=['POST'])
async def send(sid: str, segment: int):
    body = await request.body
    session[sid].reader.feed_data(body)
    data = await session[sid].read_from_buffer()
    resp = quart.Response(data)
    resp.headers['Content-Type'] = 'application/x-fcs'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/idle/<string:sid>/<int:segment>', methods=['POST'])
async def idle(sid: str, segment: int):
    # body = await request.body
    # assert body == b'\x00'
    data = await session[sid].read_from_buffer()
    resp = quart.Response(data)
    resp.headers['Content-Type'] = 'application/x-fcs'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/close/<string:sid>/<int:segment>', methods=['POST'])
async def close(sid: str, segment: int):
    # body = await request.body
    # assert body == b'\x00'
    data = await session[sid].read_from_buffer()
    session[sid].close()
    resp = quart.Response(data)
    resp.headers['Content-Type'] = 'application/x-fcs'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


async def serve_rtmpt():
    await app.run_task()


if __name__ == "__main__":
    asyncio.run(serve_rtmpt())
