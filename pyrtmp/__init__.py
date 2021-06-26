import asyncio
import os
from asyncio import StreamReader, StreamWriter, events, transports, BaseTransport, Transport, AbstractEventLoop, \
    WriteTransport, Task
from io import BytesIO
from typing import Any, Iterable, List, Optional, Mapping
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


class BufferedStreamWriter(StreamWriter):

    def __init__(self,
                 peer: str,
                 reader: StreamReader,
                 loop: events.AbstractEventLoop) -> None:
        self.peer = peer
        self.stream = BytesIO()
        self.buffer = bytearray()
        self.reader = reader
        self.loop = loop
        super().__init__(None, None, reader, loop)

    @property
    def transport(self) -> transports.BaseTransport:
        raise NotImplementedError

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    def writelines(self, data: Iterable[bytes]) -> None:
        raise NotImplementedError

    def write_eof(self) -> None:
        self.reader.feed_eof()

    def can_write_eof(self) -> bool:
        return False

    def close(self) -> None:
        assert len(self.buffer) == 0, 'Must be drained before close'
        self.reader.feed_eof()
        self.stream.close()

    def is_closing(self) -> bool:
        raise NotImplementedError

    async def wait_closed(self) -> None:
        raise NotImplementedError

    def get_extra_info(self, name: str, default: Any = ...) -> Any:
        if name == "peername":
            return self.peer
        raise NotImplementedError

    async def drain(self) -> None:
        self.stream.write(self.buffer)
        self.buffer.clear()

    async def get_buffered_data(self):
        self.stream.seek(0)
        buffer = self.stream.read()
        self.stream.truncate(0)
        return buffer


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
        self.reader: StreamReader = None
        self.writer: StreamWriter = None
        self.controller = controller
        self.task: Task = None
        super().__init__()

    def connection_made(self, transport):
        self.reader = StreamReader(loop=self.loop)
        self.writer = StreamWriter(transport,
                                   asyncio.StreamReaderProtocol(self.reader, loop=self.loop),
                                   self.reader,
                                   self.loop)
        self.task = self.loop.create_task(self.controller(self.reader, self.writer))

    def connection_lost(self, exc):
        self.reader.feed_eof()
        self.writer.close()

    def data_received(self, data):
        self.reader.feed_data(data)