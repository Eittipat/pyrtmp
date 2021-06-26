from __future__ import annotations

import logging
from asyncio import StreamWriter, Transport
from typing import Iterable

from bitstring import BitStream, BitArray

from pyrtmp import FIFOStream, random_byte_array
from pyrtmp.messages.handshake import C0, C1, C2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseChunk:

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


class RawChunk(BaseChunk):

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
        super().__init__(chunk_type, chunk_id, timestamp, msg_length, msg_type_id, msg_stream_id, payload)
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

    def as_message(self):
        from pyrtmp.messages.command import CommandMessage
        from pyrtmp.messages.protocolcontrol import \
            SetChunkSize, AbortMessage, Acknowledgement, \
            WindowAcknowledgementSize, SetPeerBandwidth
        from pyrtmp.messages.data import DataMessage
        from pyrtmp.messages.video import VideoMessage
        from pyrtmp.messages.audio import AudioMessage
        from pyrtmp.messages.usercontrol import UserControlMessage

        # protocol control message
        if self.msg_type_id == 0x01:
            return SetChunkSize.from_chunk(self)
        if self.msg_type_id == 0x02:
            return AbortMessage.from_chunk(self)
        if self.msg_type_id == 0x03:
            return Acknowledgement.from_chunk(self)
        if self.msg_type_id == 0x04:
            return UserControlMessage.from_chunk(self)
        if self.msg_type_id == 0x05:
            return WindowAcknowledgementSize.from_chunk(self)
        if self.msg_type_id == 0x06:
            return SetPeerBandwidth.from_chunk(self)

        # audio message
        if self.msg_type_id == 0x08:
            return AudioMessage.from_chunk(self)

        # video message
        if self.msg_type_id == 0x09:
            return VideoMessage.from_chunk(self)

        # AMF Based message
        # ==================

        # data message
        if self.msg_type_id == 0x12:
            return DataMessage.from_chunk(self)

        # command message
        if self.msg_type_id == 0x14:
            return CommandMessage.from_chunk(self)

        raise NotImplementedError

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


class SessionManager:

    def __init__(
            self,
            reader,
            writer,
            reader_chunk_size=128,
            writer_chunk_size=128) -> None:
        self.reader = reader
        self.writer = writer
        self.reader_chunk_size = reader_chunk_size
        self.writer_chunk_size = writer_chunk_size
        self.latest_chunks = {}
        self.fifo_reader = FIFOStream(self.reader)
        self.previous_chunk_for_writing: RawChunk = None
        super().__init__()

    @property
    def total_read_bytes(self):
        return self.fifo_reader.total_bytes

    @property
    def peername(self):
        a, b = self.writer.get_extra_info('peername')
        return f"{a}:{b}"

    def set_latest_chunk(self, chunk: RawChunk):
        self.latest_chunks[str(chunk.chunk_id)] = chunk
        self.latest_chunks["latest"] = chunk
        # logger.debug(sorted(self.latest_chunks.keys()))

    def get_previous_chunk(self, chunk_id: int) -> RawChunk:
        return self.latest_chunks[str(chunk_id)]

    async def handshake(self):
        # read c0c1
        c0 = await C0.from_stream(self.fifo_reader)
        c1 = await C1.from_stream(self.fifo_reader)
        s0 = C0(protocol_version=c0.protocol_version)
        s1 = C1(time=0, zero=0, random=random_byte_array(1528))
        s2 = C2(time1=c1.time, time2=c1.time, random=c1.random)
        s0s1s2 = BitStream()
        s0s1s2.append(s0.to_bytes())
        s0s1s2.append(s1.to_bytes())
        s0s1s2.append(s2.to_bytes())
        self.writer.write(s0s1s2.bytes)
        await self.writer.drain()
        await C2.from_stream(self.fifo_reader)
        logger.info("Handshake!")

    async def read_chunk_from_stream(self) -> Chunk:
        chunks = []
        first_chunk = await self.read_raw_chunk()
        payload_size = first_chunk.msg_length
        total_read = len(first_chunk.payload)
        payload = BitStream(first_chunk.payload)
        while payload_size > total_read:
            chunk = await self.read_raw_chunk()
            assert first_chunk.chunk_id == chunk.chunk_id
            assert first_chunk.msg_stream_id == chunk.msg_stream_id
            assert first_chunk.msg_length == chunk.msg_length
            total_read += len(chunk.payload)
            payload.append(chunk.payload)
            chunks.append(chunk)
        chunks.insert(0, first_chunk)

        # create Chunk from RawChunk
        return Chunk(
            chunk_id=chunks[0].chunk_id,
            chunk_type=chunks[0].chunk_type,
            timestamp=chunks[0].timestamp,
            msg_length=chunks[0].msg_length,
            msg_type_id=chunks[0].msg_type_id,
            msg_stream_id=chunks[0].msg_stream_id,
            payload=payload.bytes)

    async def read_raw_chunk(self) -> RawChunk:
        stream = self.fifo_reader
        chunk_size = self.reader_chunk_size

        fmt = await stream.read('uint:2')
        cs_id = await stream.read('uint:6')
        if cs_id == 0:
            cs_id = await stream.read('uint:8') + 64
        elif cs_id == 1:
            cs_id = await stream.read('uint:16') + 64
        elif cs_id == 2:
            pass

        assert fmt is not None and cs_id is not None

        if fmt == 0:
            # 11 bytes
            timestamp = await stream.read('uint:24')
            if timestamp >= 0xFFFFFF:
                timestamp = 0xFFFFFF
            msg_length = await stream.read('uint:24')
            msg_type_id = await stream.read('uint:8')
            msg_stream_id = await stream.read('uintle:32')
            sequence = 0
        elif fmt == 1:
            # 7 bytes
            previous_chunk = self.get_previous_chunk(cs_id)
            assert previous_chunk is not None
            delta = await stream.read('uint:24')
            msg_length = await stream.read('uint:24')
            msg_type_id = await stream.read('uint:8')
            msg_stream_id = previous_chunk.msg_stream_id
            timestamp = previous_chunk.timestamp + delta
            sequence = 0 if previous_chunk.is_eof else previous_chunk.raw_chunk_number + 1
        elif fmt == 2:
            # 3 bytes
            previous_chunk = self.get_previous_chunk(cs_id)
            assert previous_chunk is not None
            delta = await stream.read('uint:24')
            timestamp = previous_chunk.timestamp + delta
            msg_length = previous_chunk.msg_length
            msg_type_id = previous_chunk.msg_type_id
            msg_stream_id = previous_chunk.msg_stream_id
            sequence = 0 if previous_chunk.is_eof else previous_chunk.raw_chunk_number + 1
        elif fmt == 3:
            # 0 bytes
            # use within same chunk_id
            previous_chunk = self.get_previous_chunk(cs_id)
            assert previous_chunk is not None
            timestamp = previous_chunk.timestamp
            msg_length = previous_chunk.msg_length
            msg_type_id = previous_chunk.msg_type_id
            msg_stream_id = previous_chunk.msg_stream_id
            sequence = 0 if previous_chunk.is_eof else previous_chunk.raw_chunk_number + 1
        else:
            raise NotImplementedError

        if timestamp == 0xFFFFFF:
            timestamp = await stream.read('uint:32')

        # determine payload size
        total_read = chunk_size * sequence
        bytes_length = min(chunk_size, msg_length - total_read)
        is_eof = (msg_length - total_read - bytes_length) == 0
        payload = await stream.read(f'bytes:{bytes_length}')
        instance = RawChunk(
            chunk_type=fmt,
            chunk_id=cs_id,
            timestamp=timestamp,
            msg_length=msg_length,
            msg_type_id=msg_type_id,
            msg_stream_id=msg_stream_id,
            payload=payload,
            raw_chunk_number=sequence,
            is_eof=is_eof,
        )

        # update latest chunk
        self.set_latest_chunk(instance)

        # return
        return instance

    def write_chunk_to_stream(self, chunk: Chunk):
        chunks = chunk.to_raw_chunks(self.writer_chunk_size, self.previous_chunk_for_writing)
        for chunk in chunks:
            self.writer.write(chunk.to_bytes())
            self.previous_chunk_for_writing = chunk

    async def drain(self):
        self.previous_chunk_for_writing = None
        await self.writer.drain()
