# ~*~ coding: utf-8 ~*~

from struct import Struct
from collections import namedtuple

# System wide packet magic
SYSTEM_MAGIC = 0xACEAACEB

BIND_ADDR = "0.0.0.0"
PORT_REQUEST = 5551
PORT_REPLY = 5552

# Command codes
CMD_GET_KEY_BY_ID = 1
CMD_GET_KEY_BY_LENGTH = 2

RECV_PACKET_SIZE = 1432

KEY_LENGTH_MAX = 1384
ERROR_MESSAGE_LENGTH_MAX = 1392

RESULT_CODE_SUCCESS = 0
RESULT_CODE_THRIFT_API_CONNECTION = -201


###############################################################################
class BaseStruct(object):
    fields = ()
    struct = None

    @classmethod
    def unpack(cls, data):
        nt = namedtuple(cls.__name__, cls.fields)
        nt.as_data = lambda self: cls.struct.pack(*self)
        return nt(*cls.struct.unpack(data))

    @classmethod
    def from_fields(cls, **kwargs):
        if not set(kwargs.keys()) == set(cls.fields):
            raise TypeError('Wrong argument dict passed')
        nt = namedtuple(cls.__name__, cls.fields)
        nt.as_data = lambda self: cls.struct.pack(*self)
        return nt(**kwargs)


###############################################################################


STRUCT_REQUEST = Struct('>'
    'I'    # system_magic
    'H'    # command_magic
    'H'    # command_code
    '8x')  # reserved
STRUCT_REQUEST_FIELDS = ("system_magic", "command_magic", "command_code")


class Request(BaseStruct):
    fields = STRUCT_REQUEST_FIELDS
    struct = STRUCT_REQUEST


STRUCT_REPLY = Struct('>'
    'I'     # system_magic
    'H'     # command_magic
    'h'     # result_code
    '8x')   # reserved
STRUCT_REPLY_FIELDS = ("system_magic", "command_magic", "result_code")


class Reply(BaseStruct):
    fields = STRUCT_REPLY_FIELDS
    struct = STRUCT_REPLY


STRUCT_KEY_BY_LENGTH_REQUEST = Struct('>'
    'I')   # key_length
STRUCT_KEY_BY_LENGTH_REQUEST_FIELDS = ("key_length", )


class KeyByLengthRequest(BaseStruct):
    fields = STRUCT_KEY_BY_LENGTH_REQUEST_FIELDS
    struct = STRUCT_KEY_BY_LENGTH_REQUEST


STRUCT_KEY_BY_LENGTH_REPLY = Struct('>'
    '16s'   # key_id
    'Q'     # expiration_time
    '8x')   # reserved
STRUCT_KEY_BY_LENGTH_REPLY_FIELDS = ("key_id", "expiration_time")


class KeyByLengthReply(BaseStruct):
    fields = STRUCT_KEY_BY_LENGTH_REPLY_FIELDS
    struct = STRUCT_KEY_BY_LENGTH_REPLY


STRUCT_KEY_BY_ID_REQUEST = Struct('>'
    '16s')  # key_id
STRUCT_KEY_BY_ID_REQUEST_FIELDS = ("key_id", )


class KeyByIdRequest(BaseStruct):
    fields = STRUCT_KEY_BY_ID_REQUEST_FIELDS
    struct = STRUCT_KEY_BY_ID_REQUEST


STRUCT_ERROR_DESCRIPTION = Struct('>'
    'd'    # retry_after
    '8x')  # reserved
STRUCT_ERROR_DESCRIPTION_FIELDS = ("retry_after", )


class ErrorDescription(BaseStruct):
    fields = STRUCT_ERROR_DESCRIPTION_FIELDS
    struct = STRUCT_ERROR_DESCRIPTION
