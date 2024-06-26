import enum

from bitstring import BitArray, BitStream


class FLVTag:
    def __init__(self, stream: BitStream) -> None:
        self.tag_type = stream.read("uint:8")
        self.data_size = stream.read("uint:24")
        self.timestamp = stream.read("bytes:3")
        self.timestamp_ext = stream.read("bytes:1")
        self.stream_id = stream.read("uint:24")
        super().__init__()

    @property
    def total_timestamp(self) -> int:
        return BitArray(self.timestamp_ext + self.timestamp).int


class RawAudio:
    def __init__(self, stream: BitStream) -> None:
        format = stream.read("uint:4")
        assert format == 3
        sampling = stream.read("uint:2")
        assert sampling == 2
        size = stream.read("uint:1")
        assert size == 1
        channel = stream.read("uint:1")
        assert channel == 0
        self.bytes = stream.read("bytes")

        # new
        input = BitStream(self.bytes)
        self.pcm = []
        while input.pos < input.length:
            self.pcm.append(input.read("intle:16"))


class FLVMediaType(int, enum.Enum):
    AUDIO = 8
    VIDEO = 9
    OBJECT = 18


class FLVWriter:
    def __init__(self) -> None:
        self.prev_tag_size = 0
        super().__init__()

    def write_header(self) -> bytes:
        stream = BitStream()
        stream.append(b"FLV")
        stream.append(BitStream(uint=1, length=8))
        stream.append(BitStream(uint=5, length=8))
        stream.append(BitStream(uint=9, length=32))
        stream.append(BitStream(uint=self.prev_tag_size, length=32))
        return stream.bytes

    def write(self, timestamp: int, payload: bytes, media_type: FLVMediaType) -> bytes:
        # preprocess
        payload_size = len(payload)
        self.prev_tag_size = 11 + payload_size

        stream = BitStream()
        # tag type
        stream.append(BitArray(uint=int(media_type), length=8))
        # payload size
        stream.append(BitArray(uint=payload_size, length=24))
        # timestamp
        stream.append(BitArray(uint=timestamp & 0x00FFFFFF, length=24))
        # timestamp ext
        stream.append(BitArray(uint=timestamp >> 24, length=8))
        # stream id
        stream.append(BitArray(uint=0, length=24))
        # payload
        stream.append(payload)
        # prev tag size
        stream.append(BitArray(uint=self.prev_tag_size, length=32))
        return stream.bytes


class FLVFileWriter:
    def __init__(self, output: str) -> None:
        self.buffer = open(output, "wb")
        self.writer = FLVWriter()
        self.buffer.write(self.writer.write_header())
        super().__init__()

    def write(self, timestamp: int, payload: bytes, media_type: FLVMediaType):
        self.buffer.write(self.writer.write(timestamp, payload, media_type))
        self.buffer.flush()

    def close(self):
        self.buffer.close()
