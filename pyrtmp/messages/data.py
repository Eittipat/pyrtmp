import logging

from bitstring import BitStream

from pyrtmp.amf.serializers import AMF0Deserializer, AMF0Serializer
from pyrtmp.messages import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DataMessage(Chunk):
    # msg_type_id = 0x12,0x0F

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = AMF0Deserializer.from_stream(data)
        if signature in "@setDataFrame":
            return MetaDataMessage.from_chunk(chunk)

        logger.warning(f"Unknown data message '{signature}', use default parser")
        instance = cls(**chunk.__dict__)
        instance.command_name = signature
        return instance


class MetaDataMessage(DataMessage):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.event = AMF0Deserializer.from_stream(data)
        instance.meta = AMF0Deserializer.from_stream(data)
        return instance

    def to_raw_meta(self):
        data = BitStream()
        AMF0Serializer.write_string_object(data, self.event)
        AMF0Serializer.write_array_object(data, self.meta)
        return data.bytes
