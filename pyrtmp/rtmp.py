import asyncio
import logging
import os
import tempfile

from pyrtmp import StreamClosedException, RTMPProtocol
from pyrtmp.messages import SessionManager
from pyrtmp.messages.audio import AudioMessage
from pyrtmp.messages.command import NCConnect, NCCreateStream, NSPublish, NSCloseStream, NSDeleteStream
from pyrtmp.messages.data import MetaDataMessage
from pyrtmp.messages.protocolcontrol import WindowAcknowledgementSize, SetChunkSize, SetPeerBandwidth
from pyrtmp.messages.usercontrol import StreamBegin
from pyrtmp.messages.video import VideoMessage
from pyrtmp.misc.flvdump import FLVFile, FLVMediaType

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def simple_controller(reader, writer):
    session = SessionManager(reader=reader, writer=writer)
    flv = None
    try:
        logger.debug(f'Client connected {session.peername}')

        # do handshake
        await session.handshake()

        # read chunks
        while True:
            chunk = await session.read_chunk_from_stream()
            message = chunk.as_message()
            logger.debug(f"Receiving {str(message)} {message.chunk_id}")
            if isinstance(message, NCConnect):
                session.write_chunk_to_stream(WindowAcknowledgementSize(ack_window_size=5000000))
                session.write_chunk_to_stream(SetPeerBandwidth(ack_window_size=5000000, limit_type=2))
                session.write_chunk_to_stream(StreamBegin(stream_id=0))
                session.write_chunk_to_stream(SetChunkSize(chunk_size=8192))
                session.writer_chunk_size = 8192
                session.write_chunk_to_stream(message.create_response())
                await session.drain()
                logger.debug("Response to NCConnect")
            elif isinstance(message, WindowAcknowledgementSize):
                pass
            elif isinstance(message, NCCreateStream):
                session.write_chunk_to_stream(message.create_response())
                await session.drain()
                logger.debug("Response to NCCreateStream")
            elif isinstance(message, NSPublish):
                # create flv file at temp
                flv = FLVFile(os.path.join(tempfile.gettempdir(), message.publishing_name))
                session.write_chunk_to_stream(StreamBegin(stream_id=1))
                session.write_chunk_to_stream(message.create_response())
                await session.drain()
                logger.debug("Response to NSPublish")
            elif isinstance(message, MetaDataMessage):
                # Write meta data to file
                flv.write(0, message.to_raw_meta(), FLVMediaType.OBJECT)
            elif isinstance(message, SetChunkSize):
                session.reader_chunk_size = message.chunk_size
            elif isinstance(message, VideoMessage):
                # Write video data to file
                flv.write(message.timestamp, message.payload, FLVMediaType.VIDEO)
            elif isinstance(message, AudioMessage):
                # Write data data to file
                flv.write(message.timestamp, message.payload, FLVMediaType.AUDIO)
            elif isinstance(message, NSCloseStream):
                pass
            elif isinstance(message, NSDeleteStream):
                pass
            else:
                logger.debug(f"Unknown message {str(message)}")

    except StreamClosedException as ex:
        logger.debug(f"Client {session.peername} disconnected!")
    finally:
        if flv:
            flv.close()


async def serve_rtmp(use_protocol=True):
    loop = asyncio.get_running_loop()
    if use_protocol is True:
        server = await loop.create_server(lambda: RTMPProtocol(controller=simple_controller, loop=loop), '0.0.0.0', 1935)
    else:
        server = await asyncio.start_server(simple_controller, '0.0.0.0', 1935)
    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(serve_rtmp())
