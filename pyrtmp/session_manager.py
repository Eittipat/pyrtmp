from __future__ import annotations
from typing import Generator
from bitstring import BitStream
from pyrtmp import BitStreamReader, random_byte_array
from pyrtmp.messages import Chunk, RawChunk
from pyrtmp.messages.handshake import C0, C1, C2


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
        self.fifo_reader = BitStreamReader(self.reader)
        self.previous_chunk_for_writing: RawChunk | None = None
        self.state = {}
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

    async def read_chunks_from_stream(self) -> Generator[Chunk]:
        # stream contain many messages (full chunk)
        chunks = {}

        # process chunks
        while True:
            raw_chunk = await self.read_raw_chunk()
            if raw_chunk.chunk_id not in chunks:
                chunks[raw_chunk.chunk_id] = {
                    "payload_size": raw_chunk.msg_length,
                    "total_read": 0,
                    "children": [],
                }

            chunks[raw_chunk.chunk_id]["total_read"] += len(raw_chunk.payload)
            chunks[raw_chunk.chunk_id]["children"].append(raw_chunk)

            # check if chunk complete?
            if chunks[raw_chunk.chunk_id]["total_read"] == chunks[raw_chunk.chunk_id]["payload_size"]:
                children = chunks[raw_chunk.chunk_id]["children"]
                del chunks[raw_chunk.chunk_id]

                # de-multiplex message stream id
                msg_stream = {}
                for child in children:
                    if child.msg_stream_id not in msg_stream:
                        msg_stream[child.msg_stream_id] = []
                    msg_stream[child.msg_stream_id].append(child)

                for chunk_id in msg_stream:
                    msg_chunks = msg_stream[chunk_id]
                    payload = BitStream()
                    for ch in msg_chunks:
                        payload.append(ch.payload)
                    yield Chunk(
                        chunk_id=msg_chunks[0].chunk_id,
                        chunk_type=msg_chunks[0].chunk_type,
                        timestamp=msg_chunks[0].timestamp,
                        msg_length=msg_chunks[0].msg_length,
                        msg_type_id=msg_chunks[0].msg_type_id,
                        msg_stream_id=msg_chunks[0].msg_stream_id,
                        payload=payload.bytes,
                    )

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
