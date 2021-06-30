import asyncio
import os
from asyncio import StreamReader, StreamWriter, AbstractEventLoop, \
    WriteTransport, Task, BaseTransport
from io import BytesIO
from typing import Any, List, Optional, Mapping

from bitstring import tokenparser, BitStream


def random_byte_array(size: int) -> bytes:
    return os.urandom(size)


class StreamClosedException(Exception):
    pass


class FIFOStream:

    def __init__(self, reader: StreamReader) -> None:
        self.reader = reader
        self.buffer = BitStream()
        self.total_bytes = 0
        super().__init__()

    async def read(self, fmt):
        _, token = tokenparser(fmt)
        assert len(token) == 1
        name, length, _ = token[0]
        assert length is not None

        bit_needed = int(length) - (self.buffer.length - self.buffer.pos)
        while bit_needed > 0:
            new_data = await self.reader.read(4096)
            if len(new_data) == 0:
                raise StreamClosedException()
            self.buffer.append(new_data)
            bit_needed = int(length) - (self.buffer.length - self.buffer.pos)

        self.total_bytes += length
        value = self.buffer.read(fmt)
        del self.buffer[:length]
        self.buffer.bitpos = 0
        return value


class BufferedWriteTransport(WriteTransport):

    def __init__(self, buffer: BytesIO, extra: Optional[Mapping[Any, Any]] = ...) -> None:
        self._buffer = buffer
        self._closing = False
        self._closed = False
        super().__init__(extra)

    def set_write_buffer_limits(self, high: Optional[int] = ..., low: Optional[int] = ...) -> None:
        raise NotImplementedError

    def get_write_buffer_size(self) -> int:
        raise NotImplementedError

    def write(self, data: Any) -> None:
        self._buffer.write(data)

    def writelines(self, list_of_data: List[Any]) -> None:
        raise NotImplementedError

    def write_eof(self) -> None:
        raise NotImplementedError

    def can_write_eof(self) -> bool:
        return False

    def abort(self) -> None:
        raise NotImplementedError

    def is_closing(self) -> bool:
        return self._closing is True or self._closed is True

    def close(self) -> None:
        self._closing = True
        self._closed = True


class RTMPProtocol(asyncio.Protocol):

    def __init__(self, controller, loop: AbstractEventLoop) -> None:
        self.loop: AbstractEventLoop = loop
        self.transport: BaseTransport = None
        self.reader: StreamReader = None
        self.writer: StreamWriter = None
        self.controller = controller
        self.task: Task = None
        super().__init__()

    def connection_made(self, transport):
        self.reader = StreamReader(loop=self.loop)
        self.writer = StreamWriter(transport,
                                   self,
                                   self.reader,
                                   self.loop)
        self.task = self.loop.create_task(self.controller(self.reader, self.writer))

    def connection_lost(self, exc):
        self.reader.feed_eof()

    def data_received(self, data):
        self.reader.feed_data(data)

    async def _drain_helper(self):
        pass

    async def _get_close_waiter(self, stream: StreamWriter):
        return self.task
