from bitstring import BitStream, BitArray

from pyrtmp.messages import Chunk


class ProtocolControlMessage(Chunk):
    pass


class SetChunkSize(ProtocolControlMessage):
    chunk_size: int

    def __init__(self, chunk_size: int) -> bytes:
        assert 1 <= chunk_size <= 2147483647
        payload = BitStream()
        payload.append(BitArray(uint=chunk_size, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x01,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.chunk_size = chunk_size

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(chunk_size=data.read('uint:32'))
        return instance


class AbortMessage(ProtocolControlMessage):
    chunk_stream_id: int

    def __init__(self, chunk_stream_id: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=chunk_stream_id, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x02,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.chunk_stream_id = chunk_stream_id


class Acknowledgement(ProtocolControlMessage):
    seq_number: int

    def __init__(self, seq_number: int) -> bytes:
        payload = BitStream()
        payload.append(BitArray(uint=seq_number, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x03,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.seq_number = seq_number


class WindowAcknowledgementSize(ProtocolControlMessage):
    ack_window_size: int

    def __init__(self, ack_window_size: int):
        payload = BitStream()
        payload.append(BitArray(uint=ack_window_size, length=32))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x05,
            msg_stream_id=0,
            payload=payload.bytes)
        self.ack_window_size = ack_window_size

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        instance = cls(ack_window_size=data.read('uint:32'))
        return instance


class SetPeerBandwidth(ProtocolControlMessage):
    ack_window_size: int
    limit_type: int

    def __init__(self, ack_window_size: int, limit_type: int):
        payload = BitStream()
        payload.append(BitArray(uint=ack_window_size, length=32))
        payload.append(BitArray(uint=limit_type, length=8))
        super().__init__(
            chunk_id=2,
            chunk_type=0,
            timestamp=0,
            msg_length=len(payload.bytes),
            msg_type_id=0x06,
            msg_stream_id=0,
            payload=payload.bytes,
        )
        self.ack_window_size = ack_window_size
        self.limit_type = limit_type
