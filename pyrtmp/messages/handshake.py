from bitstring import BitStream, BitArray

from pyrtmp import FIFOStream


class C0:

    def __init__(self, protocol_version: int) -> None:
        self.protocol_version = protocol_version
        super().__init__()

    @classmethod
    async def from_stream(cls, stream: FIFOStream):
        protocol_version = await stream.read('uint:8')
        return cls(protocol_version=protocol_version)

    def to_bytes(self):
        stream = BitStream()
        stream.append(BitArray(uint=self.protocol_version, length=8))
        return stream.bytes


class C1:

    def __init__(self, time: int, zero: int, random: bytes) -> None:
        self.time = time
        self.zero = zero
        self.random = random
        super().__init__()

    @classmethod
    async def from_stream(cls, stream: FIFOStream):
        time = await stream.read('uint:32')
        zero = await stream.read('uint:32')
        rand = await stream.read('bytes:1528')
        return cls(time=time, zero=zero, random=rand)

    def to_bytes(self):
        stream = BitStream()
        stream.append(BitArray(uint=self.time, length=32))
        stream.append(BitArray(uint=self.zero, length=32))
        stream.append(BitArray(bytes=self.random, length=1528 * 8))
        return stream.bytes


class C2:

    def __init__(self, time1: int, time2: int, random: bytes) -> None:
        self.time1 = time1
        self.time2 = time2
        self.random = random
        super().__init__()

    @classmethod
    async def from_stream(cls, stream: FIFOStream):
        time1 = await stream.read('uint:32')
        time2 = await stream.read('uint:32')
        rand = await stream.read('bytes:1528')
        return cls(time1=time1, time2=time2, random=rand)

    def to_bytes(self):
        stream = BitStream()
        stream.append(BitArray(uint=self.time1, length=32))
        stream.append(BitArray(uint=self.time2, length=32))
        stream.append(BitArray(bytes=self.random, length=1528 * 8))
        return stream.bytes
