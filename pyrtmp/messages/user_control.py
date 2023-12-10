import logging

from bitstring import BitStream, BitArray

from pyrtmp.messages import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class UserControlMessage(Chunk):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = data.read('uint:16')
        if signature == 0:
            return StreamBegin.from_chunk(chunk)
        logger.warning(f"Unknown CommandMessage '{signature}', use default parser")
        instance = cls(**chunk.__dict__)
        instance.event_type = signature
        return instance


class StreamBegin(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.stream_id = data.read('uint:32')
        return instance

    def __init__(self, stream_id: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=0, length=16))
        payload.append(BitArray(uint=stream_id, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=stream_id,
            payload=payload.bytes,
        )
        self.event_type = 0
        self.stream_id = stream_id


class StreamEOF(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.stream_id = data.read('uint:32')
        return instance

    def __init__(self, stream_id: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=1, length=16))
        payload.append(BitArray(uint=stream_id, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 1
        self.stream_id = stream_id


class StreamDry(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.stream_id = data.read('uint:32')
        return instance

    def __init__(self, stream_id: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=2, length=16))
        payload.append(BitArray(uint=stream_id, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 2
        self.stream_id = stream_id


class SetBufferLength(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.stream_id = data.read('uint:32')
        instance.milliseconds = data.read('uint:32')
        return instance

    def __init__(self, stream_id: int, milliseconds: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=3, length=16))
        payload.append(BitArray(uint=stream_id, length=32))
        payload.append(BitArray(uint=milliseconds, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 3
        self.stream_id = stream_id
        self.milliseconds = milliseconds


class StreamIsRecorded(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.stream_id = data.read('uint:32')
        return instance

    def __init__(self, stream_id: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=4, length=16))
        payload.append(BitArray(uint=stream_id, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 4
        self.stream_id = stream_id


class PingRequest(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.timestamp = data.read('uint:32')
        return instance

    def __init__(self, timestamp: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=6, length=16))
        payload.append(BitArray(uint=timestamp, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 6
        self.timestamp = timestamp


class PingResponse(UserControlMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(**chunk.__dict__)
        instance.event_type = data.read('uint:16')
        instance.timestamp = data.read('uint:32')
        return instance

    def __init__(self, timestamp: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=7, length=16))
        payload.append(BitArray(uint=timestamp, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x04,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.event_type = 7
        self.timestamp = timestamp
