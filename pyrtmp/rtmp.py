from __future__ import annotations
import abc
import asyncio
import logging
from asyncio import StreamReader, StreamWriter, events
from pyrtmp import StreamClosedException
from pyrtmp.messages import Chunk
from pyrtmp.messages.audio import AudioMessage
from pyrtmp.messages.command import NCConnect, NCCreateStream, NSPublish, NSCloseStream, NSDeleteStream
from pyrtmp.messages.data import MetaDataMessage
from pyrtmp.messages.factory import MessageFactory
from pyrtmp.messages.protocol_control import WindowAcknowledgementSize, SetChunkSize, SetPeerBandwidth
from pyrtmp.messages.user_control import StreamBegin
from pyrtmp.messages.video import VideoMessage
from pyrtmp.session_manager import SessionManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseRTMPController(abc.ABC):

    async def client_callback(self, reader: StreamReader, writer: StreamWriter) -> None:
        raise NotImplementedError()

    async def on_handshake(self, session: SessionManager) -> None:
        raise NotImplementedError()

    async def on_nc_connect(self, session: SessionManager, message: NCConnect) -> None:
        raise NotImplementedError()

    async def on_window_acknowledgement_size(self, session: SessionManager, message: WindowAcknowledgementSize) -> None:
        raise NotImplementedError()

    async def on_nc_create_stream(self, session: SessionManager, message: NCCreateStream) -> None:
        raise NotImplementedError()

    async def on_ns_publish(self, session: SessionManager, message: NSPublish) -> None:
        raise NotImplementedError()

    async def on_metadata(self, session: SessionManager, message: MetaDataMessage) -> None:
        raise NotImplementedError()

    async def on_set_chunk_size(self, session: SessionManager, message: SetChunkSize) -> None:
        raise NotImplementedError()

    async def on_video_message(self, session: SessionManager, message: VideoMessage) -> None:
        raise NotImplementedError()

    async def on_audio_message(self, session: SessionManager, message: AudioMessage) -> None:
        raise NotImplementedError()

    async def on_ns_close_stream(self, session: SessionManager, message: NSCloseStream) -> None:
        raise NotImplementedError()

    async def on_ns_delete_stream(self, session: SessionManager, message: NSDeleteStream) -> None:
        raise NotImplementedError()

    async def on_unknown_message(self, session: SessionManager, message: Chunk) -> None:
        raise NotImplementedError()

    async def on_stream_closed(self, session: SessionManager, exception: StreamClosedException) -> None:
        raise NotImplementedError()

    async def cleanup(self, session: SessionManager) -> None:
        raise NotImplementedError()


class SimpleRTMPController(BaseRTMPController):

    async def client_callback(self, reader: StreamReader, writer: StreamWriter) -> None:
        # create session per client
        session = SessionManager(reader=reader, writer=writer)
        logger.debug(f'Client connected {session.peername}')

        try:
            # do handshake
            await self.on_handshake(session)
            logger.debug(f"Handshake! {session.peername}")

            # read chunks
            async for chunk in session.read_chunks_from_stream():
                message = MessageFactory.from_chunk(chunk)
                # logger.debug(f"Receiving {str(message)} {message.chunk_id}")
                if isinstance(message, NCConnect):
                    await self.on_nc_connect(session, message)
                elif isinstance(message, WindowAcknowledgementSize):
                    await self.on_window_acknowledgement_size(session, message)
                elif isinstance(message, NCCreateStream):
                    await self.on_nc_create_stream(session, message)
                elif isinstance(message, NSPublish):
                    await self.on_ns_publish(session, message)
                elif isinstance(message, MetaDataMessage):
                    await self.on_metadata(session, message)
                elif isinstance(message, SetChunkSize):
                    await self.on_set_chunk_size(session, message)
                elif isinstance(message, VideoMessage):
                    await self.on_video_message(session, message)
                elif isinstance(message, AudioMessage):
                    await self.on_audio_message(session, message)
                elif isinstance(message, NSCloseStream):
                    await self.on_ns_close_stream(session, message)
                elif isinstance(message, NSDeleteStream):
                    await self.on_ns_delete_stream(session, message)
                else:
                    await self.on_unknown_message(session, message)

        except StreamClosedException as ex:
            logger.debug(f'Client disconnected {session.peername}')
            await self.on_stream_closed(session, ex)
        except Exception as ex:
            logger.exception(ex)
        finally:
            await self.cleanup(session)

    async def on_handshake(self, session) -> None:
        await session.handshake()

    async def on_nc_connect(self, session, message) -> None:
        session.write_chunk_to_stream(WindowAcknowledgementSize(ack_window_size=5000000))
        session.write_chunk_to_stream(SetPeerBandwidth(ack_window_size=5000000, limit_type=2))
        session.write_chunk_to_stream(StreamBegin(stream_id=0))
        session.write_chunk_to_stream(SetChunkSize(chunk_size=8192))
        session.writer_chunk_size = 8192
        session.write_chunk_to_stream(message.create_response())
        await session.drain()

    async def on_window_acknowledgement_size(self, session, message) -> None:
        pass

    async def on_nc_create_stream(self, session, message) -> None:
        session.write_chunk_to_stream(message.create_response())
        await session.drain()

    async def on_ns_publish(self, session, message) -> None:
        session.write_chunk_to_stream(StreamBegin(stream_id=1))
        session.write_chunk_to_stream(message.create_response())
        await session.drain()

    async def on_metadata(self, session, message) -> None:
        pass

    async def on_set_chunk_size(self, session, message) -> None:
        session.reader_chunk_size = message.chunk_size

    async def on_video_message(self, session, message) -> None:
        pass

    async def on_audio_message(self, session, message) -> None:
        pass

    async def on_ns_close_stream(self, session, message) -> None:
        pass

    async def on_ns_delete_stream(self, session, message) -> None:
        pass

    async def on_unknown_message(self, session, message) -> None:
        logger.warning(f"Unknown message {str(message)}")

    async def on_stream_closed(self, session: SessionManager, exception: StreamClosedException) -> None:
        pass

    async def cleanup(self, session: SessionManager) -> None:
        logger.debug(f'Clean up {session.peername}')


class RTMPProtocol(asyncio.StreamReaderProtocol):

    def __init__(self, controller: BaseRTMPController) -> None:
        self.callback = controller.client_callback
        self.loop = events.get_event_loop()
        super().__init__(
            StreamReader(loop=self.loop),
            self.callback,
            loop=self.loop,
        )


class SimpleRTMPServer:

    def __init__(self):
        self.server = None
        self.on_start = None
        self.on_stop = None

    def _signal_on_start(self):
        if self.on_start:
            self.on_start()

    def _signal_on_stop(self):
        if self.on_stop:
            self.on_stop()

    async def create(self, host: str, port: int):
        loop = asyncio.get_event_loop()
        self.server = await loop.create_server(
            lambda: RTMPProtocol(controller=SimpleRTMPController()),
            host=host,
            port=port,
        )

    async def start(self):
        addr = self.server.sockets[0].getsockname()
        await self.server.start_serving()
        self._signal_on_start()
        logger.info(f'Serving on {addr}')

    async def wait_closed(self):
        await self.server.wait_closed()

    async def stop(self):
        self.server.close()
        self._signal_on_stop()


async def main():
    server = SimpleRTMPServer()
    await server.create(host='0.0.0.0', port=1935)
    await server.start()
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
