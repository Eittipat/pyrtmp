from typing import Any

from bitstring import BitArray, BitStream

from pyrtmp.amf.types import AMF0


class AMF0Serializer:
    @classmethod
    def create_object(cls, data: BitStream, value):
        if isinstance(value, str):
            cls.write_string_object(data, value)
        elif isinstance(value, bool):
            cls.write_boolean_object(data, value)
        elif isinstance(value, float):
            cls.write_number_object(data, value)
        elif isinstance(value, int):
            cls.write_number_object(data, value)
        elif isinstance(value, dict):
            cls.write_object_object(data, value)
        elif isinstance(value, list):
            cls.write_array_object(data, value)
        elif value is None:
            cls.write_null_object(data)
        else:
            raise NotImplementedError

    @classmethod
    def write_boolean_object(cls, data: BitStream, value: bool):
        pos = data.pos
        data.append(BitArray(uint=AMF0.BOOLEAN, length=8))
        data.append(BitArray(uint=0 if value is False else 1, length=8))
        data.pos = pos

    @classmethod
    def write_string_object(cls, data: BitStream, value: str):
        pos = data.pos
        data.append(BitArray(uint=AMF0.STRING, length=8))
        data.append(BitArray(uint=len(value), length=16))
        data.append(BitArray(bytes=value.encode(), length=len(value) * 8))
        data.pos = pos

    @classmethod
    def write_number_object(cls, data: BitStream, value: float):
        pos = data.pos
        data.append(BitArray(uint=AMF0.NUMBER, length=8))
        data.append(BitArray(float=value, length=64))
        data.pos = pos

    @classmethod
    def write_null_object(cls, data: BitStream):
        pos = data.pos
        data.append(BitArray(uint=AMF0.NULL, length=8))
        data.pos = pos

    @classmethod
    def write_object_object(cls, data: BitStream, value: dict):
        pos = data.pos
        data.append(BitArray(uint=AMF0.OBJECT, length=8))
        for k, v in value.items():
            data.append(BitArray(uint=len(k), length=16))
            data.append(BitArray(bytes=k.encode(), length=len(k) * 8))
            cls.create_object(data, v)
        data.append(BitArray(uint=AMF0.OBJECT_END, length=24))
        data.pos = pos

    @classmethod
    def write_array_object(cls, data: BitStream, value: list):
        pos = data.pos
        data.append(BitArray(uint=AMF0.ARRAY, length=8))
        data.append(BitArray(uint=len(value), length=32))
        for item in value:
            for key in item:
                property_key = key.encode()
                data.append(BitArray(uint=len(property_key), length=16))
                data.append(BitArray(bytes=property_key, length=len(property_key) * 8))
                cls.create_object(data, item[key])
        data.append(BitArray(uint=AMF0.OBJECT_END, length=24))
        data.pos = pos


class AMF0Deserializer:
    @classmethod
    def from_stream(cls, data: BitStream) -> Any:
        # determine object type
        obj_type = data.peek("uint:8")
        if obj_type == AMF0.STRING:
            return cls.to_string_object(data)
        if obj_type == AMF0.NUMBER:
            return cls.to_number_object(data)
        if obj_type == AMF0.OBJECT:
            return cls.to_object_object(data)
        if obj_type == AMF0.NULL:
            return cls.to_null_object(data)
        if obj_type == AMF0.ARRAY:
            return cls.to_array_object(data)
        if obj_type == AMF0.BOOLEAN:
            return cls.to_boolean_object(data)
        raise NotImplementedError

    @classmethod
    def to_boolean_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.BOOLEAN
        value = data.read("uint:8")
        return False if value == 0 else True

    @classmethod
    def to_string_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.STRING
        obj_length = data.read("uint:16")
        return data.read(f"bytes:{obj_length}").decode()

    @classmethod
    def to_number_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.NUMBER
        return data.read("float:64")

    @classmethod
    def to_null_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.NULL
        return None

    @classmethod
    def to_object_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.OBJECT
        obj = {}
        ending = f"0000{int(AMF0.OBJECT_END):02x}"
        while data.peek("bytes:3").hex() != ending:
            # read property name
            size = data.read("uint:16")
            property_name = data.read(f"bytes:{size}").decode()
            # read object value (AMF0)
            property_value = cls.from_stream(data)
            obj[property_name] = property_value
        return obj

    @classmethod
    def to_array_object(cls, data: BitStream):
        obj_type = data.read("uint:8")
        assert obj_type == AMF0.ARRAY
        arr = []
        count = data.read("uint:32")
        ending = f"0000{int(AMF0.OBJECT_END):02x}"
        while data.peek("bytes:3").hex() != ending:
            size = data.read("uint:16")
            property_name = data.read(f"bytes:{size}").decode()
            # read object value (AMF0)
            property_value = cls.from_stream(data)
            arr.append({property_name: property_value})
        assert len(arr) == count
        return arr
