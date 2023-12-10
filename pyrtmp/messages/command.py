from __future__ import annotations

import logging

from bitstring import BitStream

from pyrtmp.amf.serializers import AMF0Deserializer, AMF0Serializer
from pyrtmp.messages import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CommandMessage(Chunk):

    def __init__(self, command_name: str, **kwargs):
        super().__init__(**kwargs)
        self.command_name = command_name

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        signature = AMF0Deserializer.from_stream(data)
        if signature in NetConnectionCommand.valid_commands:
            return NetConnectionCommand.from_chunk(chunk)
        if signature in NetStreamCommand.valid_commands:
            return NetStreamCommand.from_chunk(chunk)

        logger.warning(f"Unknown CommandMessage '{signature}', use default parser")
        instance = cls(
            command_name=signature,
            **chunk.__dict__,
        )
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
        instance = cls(
            command_name=signature,
            **chunk.__dict__,
        )
        return instance


class NCConnect(NetConnectionCommand):

    def __init__(
            self,
            transaction_id: int,
            command_object: dict,
            optional_user_arguments: dict | None,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.transaction_id = transaction_id
        self.command_object = command_object
        self.optional_user_arguments = optional_user_arguments

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        command_name = AMF0Deserializer.from_stream(data)
        transaction_id = AMF0Deserializer.from_stream(data)
        command_object = AMF0Deserializer.from_stream(data)
        if data.bytepos - len(data.bytes) > 0:
            optional_user_arguments = AMF0Deserializer.from_stream(data)
        else:
            optional_user_arguments = None
        return cls(
            command_name=command_name,
            transaction_id=transaction_id,
            command_object=command_object,
            optional_user_arguments=optional_user_arguments,
            **chunk.__dict__,
        )

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
            payload=data.bytes,
        )


class NCCall(NetConnectionCommand):
    pass


class NCClose(NetConnectionCommand):
    pass


class NCCreateStream(NetConnectionCommand):

    def __init__(self, transaction_id: int, command_object: dict, **kwargs):
        super().__init__(**kwargs)
        self.transaction_id = transaction_id
        self.command_object = command_object

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        command_name = AMF0Deserializer.from_stream(data)
        transaction_id = AMF0Deserializer.from_stream(data)
        command_object = AMF0Deserializer.from_stream(data)
        return cls(
            command_name=command_name,
            transaction_id=transaction_id,
            command_object=command_object,
            **chunk.__dict__,
        )

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
            payload=data.bytes,
        )


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
        return cls(
            command_name=signature,
            **chunk.__dict__,
        )


class NSPlay(NetConnectionCommand):
    pass


class NSPlay2(NetConnectionCommand):
    pass


class NSDeleteStream(NetConnectionCommand):

    def __init__(
            self,
            stream_id: int,
            transaction_id: int,
            command_object: dict,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.stream_id = stream_id
        self.transaction_id = transaction_id
        self.command_object = command_object

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        command_name = AMF0Deserializer.from_stream(data)
        transaction_id = AMF0Deserializer.from_stream(data)
        command_object = AMF0Deserializer.from_stream(data)
        stream_id = AMF0Deserializer.from_stream(data)
        return cls(
            command_name=command_name,
            transaction_id=transaction_id,
            command_object=command_object,
            stream_id=stream_id,
            **chunk.__dict__,
        )


class NSCloseStream(NetConnectionCommand):

    def __init__(
            self,
            transaction_id: int,
            command_object: dict,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.transaction_id = transaction_id
        self.command_object = command_object

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        command_name = AMF0Deserializer.from_stream(data)
        transaction_id = AMF0Deserializer.from_stream(data)
        command_object = AMF0Deserializer.from_stream(data)
        return cls(
            command_name=command_name,
            transaction_id=transaction_id,
            command_object=command_object,
            **chunk.__dict__,
        )


class NSReceiveAudio(NetConnectionCommand):
    pass


class NSReceiveVideo(NetConnectionCommand):
    pass


class NSPublish(NetConnectionCommand):

    def __init__(
            self,
            transaction_id: int,
            command_object: dict,
            publishing_name: str,
            publishing_type: str,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.transaction_id = transaction_id
        self.command_object = command_object
        self.publishing_name = publishing_name
        self.publishing_type = publishing_type

    @classmethod
    def from_chunk(cls, chunk: Chunk):
        data = BitStream(chunk.payload)
        command_name = AMF0Deserializer.from_stream(data)
        transaction_id = AMF0Deserializer.from_stream(data)
        command_object = AMF0Deserializer.from_stream(data)
        publishing_name = AMF0Deserializer.from_stream(data)
        publishing_type = AMF0Deserializer.from_stream(data)
        return cls(
            command_name=command_name,
            transaction_id=transaction_id,
            command_object=command_object,
            publishing_name=publishing_name,
            publishing_type=publishing_type,
            **chunk.__dict__,
        )

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
            payload=data.bytes,
        )


class NSSeek(NetConnectionCommand):
    pass


class NSPause(NetConnectionCommand):
    pass
