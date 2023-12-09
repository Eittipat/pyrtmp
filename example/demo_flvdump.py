import asyncio
import os
import logging

from pyrtmp import StreamClosedException
from pyrtmp.flv import FLVFileWriter, FLVMediaType
from pyrtmp.messages import SessionManager
from pyrtmp.rtmp import SimpleRTMPController, RTMPProtocol

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RTMP2FLVController(SimpleRTMPController):

    def __init__(self, output_directory: str):
        self.output_directory = output_directory
        super().__init__()

    async def on_ns_publish(self, session, message) -> None:
        publishing_name = message.publishing_name
        file_path = os.path.join(self.output_directory, f"{publishing_name}.flv")
        session.state = FLVFileWriter(output=file_path)
        await super().on_ns_publish(session, message)

    async def on_metadata(self, session, message) -> None:
        session.state.write(0, message.to_raw_meta(), FLVMediaType.OBJECT)
        await super().on_metadata(session, message)

    async def on_video_message(self, session, message) -> None:
        session.state.write(message.timestamp, message.payload, FLVMediaType.VIDEO)
        await super().on_video_message(session, message)

    async def on_audio_message(self, session, message) -> None:
        session.state.write(message.timestamp, message.payload, FLVMediaType.AUDIO)
        await super().on_audio_message(session, message)

    async def on_stream_closed(self, session: SessionManager, exception: StreamClosedException) -> None:
        session.state.close()
        await super().on_stream_closed(session, exception)


async def serve_rtmp(output_directory: str):
    loop = asyncio.get_event_loop()
    server = await loop.create_server(
        lambda: RTMPProtocol(controller=RTMP2FLVController(output_directory)),
        host='0.0.0.0',
        port=1935
    )
    addr = server.sockets[0].getsockname()
    logger.info(f'FLV output to {output_directory}')
    logger.info(f'Serving on {addr}')
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    asyncio.run(serve_rtmp(current_dir))
