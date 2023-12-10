from __future__ import annotations
from typing import Iterable
from bitstring import BitStream, BitArray

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseChunk:
    chunk_type: int
    chunk_id: int
    timestamp: int
    msg_length: int
    msg_type_id: int
    msg_stream_id: int
    payload: bytes

    def __init__(
            self,
            chunk_type: int,
            chunk_id: int,
            timestamp: int,
            msg_length: int,
            msg_type_id: int,
            msg_stream_id: int,
            payload: bytes,
    ) -> None:
        self.chunk_type = chunk_type
        self.chunk_id = chunk_id
        self.timestamp = timestamp
        self.msg_length = msg_length
        self.msg_type_id = msg_type_id
        self.msg_stream_id = msg_stream_id
        self.payload = payload
        super().__init__()

    def __str__(self) -> str:
        buffer = f"{self.__class__.__name__}"
        buffer += f"(chunk_type: {self.chunk_type},"
        buffer += f"chunk_id: {self.chunk_id},"
        buffer += f"timestamp: {self.timestamp},"
        buffer += f"msg_length: {self.msg_length},"
        buffer += f"msg_type_id: {self.msg_type_id},"
        buffer += f"msg_stream_id: {self.msg_stream_id},"
        buffer += f"payload: {len(self.payload)})"
        return buffer


class RawChunk(BaseChunk):
    raw_chunk_number: int = 0,
    is_eof: bool = False,

    def __init__(
            self,
            chunk_type: int,
            chunk_id: int,
            timestamp: int,
            msg_length: int,
            msg_type_id: int,
            msg_stream_id: int,
            payload: bytes,
            raw_chunk_number: int = 0,
            is_eof: bool = False,
    ) -> None:
        super().__init__(
            chunk_type=chunk_type,
            chunk_id=chunk_id,
            timestamp=timestamp,
            msg_length=msg_length,
            msg_type_id=msg_type_id,
            msg_stream_id=msg_stream_id,
            payload=payload,
        )
        self.raw_chunk_number = raw_chunk_number
        self.is_eof = is_eof

    def to_bytes(self) -> bytes:
        stream = BitStream()

        # basic header
        stream.append(BitArray(uint=self.chunk_type, length=2))
        if self.chunk_id <= 63:
            # reserved order 0,1,2 included
            stream.append(BitArray(uint=self.chunk_id, length=6))
        elif 64 <= self.chunk_id <= 319:
            stream.append(BitArray(uint=0, length=6))
            stream.append(BitArray(uint=self.chunk_id - 64, length=8))
        elif 320 <= self.chunk_id <= 65599:
            stream.append(BitArray(uint=1, length=6))
            stream.append(BitArray(uint=self.chunk_id - 64, length=16))
        else:
            raise NotImplementedError

        # message header
        timestamp = 0xFFFFFF if self.timestamp >= 0xFFFFFF else self.timestamp

        if self.chunk_type == 0:
            # type 0 body
            stream.append(BitArray(uint=timestamp, length=24))
            stream.append(BitArray(uint=self.msg_length, length=24))
            stream.append(BitArray(uint=self.msg_type_id, length=8))
            stream.append(BitArray(uintle=self.msg_stream_id, length=32))
        elif self.chunk_type == 1:
            # type 1 body
            stream.append(BitArray(uint=timestamp, length=24))
            stream.append(BitArray(uint=self.msg_length, length=24))
            stream.append(BitArray(uint=self.msg_type_id, length=8))
        elif self.chunk_type == 2:
            # type 2 body
            stream.append(BitArray(uint=timestamp, length=24))
        elif self.chunk_type == 3:
            pass
        else:
            raise NotImplementedError

        # extend timestamp if needed
        if timestamp == 0xFFFFFF:
            stream.append(BitArray(uint=self.timestamp, length=32))

        stream.append(self.payload)

        return stream.bytes


class Chunk(BaseChunk):

    def print_debug(self):
        logger.debug(f"======{self.__class__}======")
        for key in self.__dict__.keys():
            if key.startswith("_"):
                continue

            value = self.__dict__[key]
            logger.debug(f"{key} => {value}")

    def to_raw_chunks(self, chunk_size: int, previous: RawChunk = None) -> Iterable[RawChunk]:
        chunks = []
        payload = self.payload
        # timestamp within a chunk must be the same
        timedelta = 0 if previous is None else self.timestamp - previous.timestamp
        # chunk_number is message level
        chunk_number = 0
        # determine chunk type based on previous raw chunk of another message
        chunk_type = 0
        if previous and previous.timestamp > timedelta:
            raise NotImplementedError
        if previous and previous.msg_stream_id == self.msg_stream_id:
            chunk_type = 1
        if chunk_type == 1 and previous.msg_length == self.msg_length and previous.msg_type_id == self.msg_type_id:
            chunk_type = 2
        if chunk_type == 3 and timedelta == 0:
            chunk_type = 3

        while len(payload) > 0:
            bytes_length = min(chunk_size, len(payload))
            is_eof = bytes_length - chunk_size == 0
            raw_chunk = RawChunk(
                chunk_type=chunk_type,
                chunk_id=self.chunk_id,
                timestamp=timedelta,
                msg_length=self.msg_length,
                msg_type_id=self.msg_type_id,
                msg_stream_id=self.msg_stream_id,
                payload=payload[:bytes_length],
                raw_chunk_number=chunk_number,
                is_eof=is_eof)
            chunks.append(raw_chunk)
            chunk_number += 1
            chunk_type = 3  # next raw chunk always 3
            payload = payload[bytes_length:]
        return chunks
