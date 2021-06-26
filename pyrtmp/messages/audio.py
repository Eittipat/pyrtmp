from bitstring import BitStream
from pyrtmp.messages import Chunk


class AudioMessage(Chunk):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.control = data.read('bytes:1')
        instance.data = data.read(f'bytes:{instance.msg_length - 1}')
        return instance

