import asyncio
import unittest

from asyncio import StreamReader
from bitstring import BitArray, BitStream
from pyrtmp import BitStreamReader
from pyrtmp.amf.serializers import AMF0Serializer


class MockStreamReader(StreamReader):

    def __init__(self):
        super().__init__()
        self.mock_data = None

    async def read(self, n=...):
        while self.mock_data is None:
            await asyncio.sleep(0.1)
        data = self.mock_data
        self.mock_data = None
        return data

    def set_mock_data(self, data: bytes):
        self.mock_data = data


class TestBitStreamReader(unittest.IsolatedAsyncioTestCase):

    async def test_enough_data(self):
        # given
        mock_data = BitArray("0b1111111100000000100010001000000011011011").bytes
        mock_reader = MockStreamReader()
        mock_reader.set_mock_data(mock_data)
        stream = BitStreamReader(reader=mock_reader)

        # when
        uint8 = await stream.read("uint:8")
        int32 = await stream.read("int:32")

        # then
        self.assertEqual(uint8, 255)
        self.assertEqual(int32, 8945883)

    async def test_not_enough_data(self):
        # given
        mock_reader = MockStreamReader()
        stream = BitStreamReader(reader=mock_reader)

        async def feed_data():
            mock_reader.set_mock_data(b'\xff')
            await asyncio.sleep(0.5)
            mock_reader.set_mock_data(b'\x00')
            await asyncio.sleep(0.5)
            mock_reader.set_mock_data(b'\x88')
            await asyncio.sleep(0.5)
            mock_reader.set_mock_data(b'\x80')
            await asyncio.sleep(0.5)
            mock_reader.set_mock_data(b'\xdb')
            print("feed_data done")

        task = asyncio.create_task(feed_data())

        # when
        uint8 = await stream.read("uint:8")
        int32 = await stream.read("int:32")

        await task

        # then
        self.assertEqual(uint8, 255)
        self.assertEqual(int32, 8945883)


class AMF0SerializerTestCase(unittest.TestCase):

    def test_write_boolean_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_boolean_object(data, True)

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 8 + 8)
        self.assertEqual(data.bytes, b'\x01\x01')

    def test_write_string_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_string_object(data, "hello world")

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 8 + 16 + len("hello world") * 8)
        self.assertEqual(data.bytes, b'\x02\x00\x0bhello world')

    def test_write_number_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_number_object(data, 3.1415)

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 72)
        self.assertEqual(data.bytes, b'\x00@\t!\xca\xc0\x83\x12o')

    def test_write_null_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_null_object(data)

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 8)
        self.assertEqual(data.bytes, b'\x05')

    def test_write_object_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_object_object(data, {
            "key1": "value1",
            "key2": 2,
            "key3": True,
        })

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 336)
        self.assertEqual(data.bytes,
                         b'\x03\x00\x04' +
                         b'key1\x02\x00\x06value1\x00\x04' +
                         b'key2\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x04' +
                         b'key3\x01\x01\x00\x00\t')

    def test_write_array_object(self):
        # given
        data = BitStream()

        # when
        AMF0Serializer.write_array_object(data, [
            {"key1": "value1"},
            {"key2": 2},
            {"key3": True},
        ])

        # then
        self.assertEqual(data.pos, 0)
        self.assertEqual(data.length, 368)
        self.assertEqual(data.bytes,
                         b'\x08\x00\x00\x00\x03\x00\x04'
                         + b'key1\x02\x00\x06value1\x00\x04'
                         + b'key2\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x04'
                         + b'key3\x01\x01\x00\x00\t')
