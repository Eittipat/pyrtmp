import os
from asyncio import StreamReader, WriteTransport
from collections.abc import Mapping
from io import BytesIO
from typing import Any

from bitstring import BitStream
from bitstring.bits import Bits
from bitstring.utils import tokenparser


def random_byte_array(size: int) -> bytes:
    return os.urandom(size)


class StreamClosedException(Exception):
    pass


class BitStreamReader:
    def __init__(self, reader: StreamReader) -> None:
        self.reader = reader
        self.buffer = BitStream()
        self.total_bytes = 0
        super().__init__()

    async def read(self, fmt) -> int | float | str | Bits | bool | bytes | None:
        _, token = tokenparser(fmt)
        assert len(token) == 1
        name, length, _ = token[0]
        assert length is not None

        bit_needed = int(length) - (self.buffer.length - self.buffer.pos)
        while bit_needed > 0:
            new_data = await self.reader.read(4096)
            if len(new_data) == 0:
                raise StreamClosedException()
            self._append(new_data)
            bit_needed = int(length) - (self.buffer.length - self.buffer.pos)

        self.total_bytes += length
        value = self.buffer.read(fmt)
        del self.buffer[:length]
        self.buffer.bitpos = 0
        return value

    def _append(self, data: bytes) -> None:
        pos = self.buffer.pos
        self.buffer.append(data)
        self.buffer.pos = pos


class BufferedWriteTransport(WriteTransport):
    def __init__(self, buffer: BytesIO, extra: Mapping[Any, Any] | None = ...) -> None:
        self._buffer = buffer
        self._closing = False
        self._closed = False
        super().__init__(extra)

    def set_write_buffer_limits(self, high: int | None = ..., low: int | None = ...) -> None:
        raise NotImplementedError

    def get_write_buffer_size(self) -> int:
        raise NotImplementedError

    def write(self, data: Any) -> None:
        self._buffer.write(data)

    def writelines(self, list_of_data: list[Any]) -> None:
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
