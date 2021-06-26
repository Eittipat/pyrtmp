import logging

from bitstring import BitStream

from pyrtmp.amf.serializers import AMF0Deserializer, AMF0Serializer
from pyrtmp.messages import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CommandMessage(Chunk):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = AMF0Deserializer.from_stream(data)
        if signature in NetConnectionCommand.valid_commands:
            return NetConnectionCommand.from_chunk(chunk)
        if signature in NetStreamCommand.valid_commands:
            return NetStreamCommand.from_chunk(chunk)

        logger.warning(f"Unknown CommandMessage '{signature}', use default parser")
        instance = cls(**chunk.__dict__)
        instance.command_name = signature
        return instance


class NetConnectionCommand(CommandMessage):
    valid_commands = [
        "connect",
        "call",
        "close",
        "createStream",
    ]

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = AMF0Deserializer.from_stream(data)
        if signature == "connect":
            return NCConnect.from_chunk(chunk)
        if signature == "createStream":
            return NCCreateStream.from_chunk(chunk)

        logger.warning(f"Unknown NetConnectionCommand '{signature}', use default parser")
        instance = cls(**chunk.__dict__)
        instance.command_name = signature
        return instance


class NCConnect(NetConnectionCommand):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.transaction_id = AMF0Deserializer.from_stream(data)
        instance.command_object = AMF0Deserializer.from_stream(data)
        if data.bytepos - len(data.bytes) > 0:
            instance.optional_user_arguments = AMF0Deserializer.from_stream(data)
        else:
            instance.optional_user_arguments = None
        return instance

    def create_response(self) -> Chunk:
        data = BitStream()

        # payload
        AMF0Serializer.create_object(data, "_result")
        AMF0Serializer.create_object(data, 1)
        AMF0Serializer.create_object(data, {
            "fmsVer": "FMS/3,0,123",
            "capabilities": 31,
        })
        AMF0Serializer.create_object(data, {
            "level": "status",
            "code": "NetConnection.Connect.Success",
            "description": "Connection succeeds",
            "objectEncoding": 0,
        })

        return Chunk(
            chunk_type=0,
            chunk_id=self.chunk_id,
            timestamp=0,
            msg_length=len(data.bytes),
            msg_type_id=0x14,
            msg_stream_id=0,
            payload=data.bytes)


class NCCall(NetConnectionCommand):
    pass


class NCClose(NetConnectionCommand):
    pass


class NCCreateStream(NetConnectionCommand):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.transaction_id = AMF0Deserializer.from_stream(data)
        instance.command_object = AMF0Deserializer.from_stream(data)
        return instance

    def create_response(self) -> Chunk:
        data = BitStream()

        # payload
        AMF0Serializer.create_object(data, "_result")
        AMF0Serializer.create_object(data, self.transaction_id)
        AMF0Serializer.create_object(data, None)
        AMF0Serializer.create_object(data, 1)

        return Chunk(
            chunk_type=0,
            chunk_id=self.chunk_id,
            timestamp=0,
            msg_length=len(data.bytes),
            msg_type_id=0x14,
            msg_stream_id=0,
            payload=data.bytes)


class NetStreamCommand(CommandMessage):
    valid_commands = [
        "play",
        "play2",
        "deleteStream",
        "closeStream",
        "receiveAudio",
        "receiveVideo",
        "publish",
        "seek",
        "pause",
        "onStatus",
    ]

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = AMF0Deserializer.from_stream(data)
        if signature == "publish":
            return NSPublish.from_chunk(chunk)
        if signature == "closeStream":
            return NSCloseStream.from_chunk(chunk)
        if signature == "deleteStream":
            return NSDeleteStream.from_chunk(chunk)

        logger.warning(f"Unknown NetStreamCommand '{signature}', use default parser")
        instance = cls(**chunk.__dict__)
        instance.command_name = signature
        return instance


class NSPlay(NetConnectionCommand):
    pass


class NSPlay2(NetConnectionCommand):
    pass


class NSDeleteStream(NetConnectionCommand):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.transaction_id = AMF0Deserializer.from_stream(data)
        instance.command_object = AMF0Deserializer.from_stream(data)
        instance.stream_id = AMF0Deserializer.from_stream(data)
        return instance


class NSCloseStream(NetConnectionCommand):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.transaction_id = AMF0Deserializer.from_stream(data)
        instance.command_object = AMF0Deserializer.from_stream(data)
        return instance


class NSReceiveAudio(NetConnectionCommand):
    pass


class NSReceiveVideo(NetConnectionCommand):
    pass


class NSPublish(NetConnectionCommand):

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        instance = cls(**chunk.__dict__)
        data = BitStream(instance.payload)
        instance.command_name = AMF0Deserializer.from_stream(data)
        instance.transaction_id = AMF0Deserializer.from_stream(data)
        instance.command_object = AMF0Deserializer.from_stream(data)
        instance.publishing_name = AMF0Deserializer.from_stream(data)
        instance.publishing_type = AMF0Deserializer.from_stream(data)
        return instance

    def create_response(self) -> Chunk:
        data = BitStream()

        # payload
        AMF0Serializer.create_object(data, "onStatus")
        AMF0Serializer.create_object(data, 0)
        AMF0Serializer.create_object(data, None)
        AMF0Serializer.create_object(data, {
            "level": "status",
            "code": "NetStream.Publish.Start",
            "description": "Start publishing"
        })

        return Chunk(
            chunk_type=0,
            chunk_id=3,
            timestamp=0,
            msg_length=len(data.bytes),
            msg_type_id=0x14,
            msg_stream_id=self.msg_stream_id,
            payload=data.bytes)


class NSSeek(NetConnectionCommand):
    pass


class NSPause(NetConnectionCommand):
    pass
