from pyrtmp.messages import Chunk
from pyrtmp.messages.audio import AudioMessage
from pyrtmp.messages.command import CommandMessage
from pyrtmp.messages.data import DataMessage
from pyrtmp.messages.protocol_control import (
    SetChunkSize, AbortMessage, Acknowledgement,
    WindowAcknowledgementSize, SetPeerBandwidth,
)
from pyrtmp.messages.user_control import UserControlMessage
from pyrtmp.messages.video import VideoMessage


class MessageFactory:

    @classmethod
    def from_chunk(cls, chunk: Chunk):

        # protocol control message
        if chunk.msg_type_id == 0x01:
            return SetChunkSize.from_chunk(chunk)
        if chunk.msg_type_id == 0x02:
            return AbortMessage.from_chunk(chunk)
        if chunk.msg_type_id == 0x03:
            return Acknowledgement.from_chunk(chunk)
        if chunk.msg_type_id == 0x04:
            return UserControlMessage.from_chunk(chunk)
        if chunk.msg_type_id == 0x05:
            return WindowAcknowledgementSize.from_chunk(chunk)
        if chunk.msg_type_id == 0x06:
            return SetPeerBandwidth.from_chunk(chunk)

        # audio message
        if chunk.msg_type_id == 0x08:
            return AudioMessage.from_chunk(chunk)

        # video message
        if chunk.msg_type_id == 0x09:
            return VideoMessage.from_chunk(chunk)

        # AMF Based message
        # ==================

        # data message
        if chunk.msg_type_id == 0x12:
            return DataMessage.from_chunk(chunk)

        # command message
        if chunk.msg_type_id == 0x14:
            return CommandMessage.from_chunk(chunk)

        raise NotImplementedError
