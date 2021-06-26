from enum import Enum


class AMF0(int, Enum):
    NUMBER = 0x00
    BOOLEAN = 0x01
    STRING = 0x02
    OBJECT = 0x03
    NULL = 0x05
    ARRAY = 0x08
    OBJECT_END = 0x09


