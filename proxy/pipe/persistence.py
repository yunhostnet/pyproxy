from io import BufferedIOBase
from uuid import UUID

from proxy.parser.parser_utils import get_word, intialize_parser, parse
from proxy.pipe.communication import RequestResponse

from proxy.parser.http_parser import HttpMessage, get_http_request, get_line


def serialize_message(msg: HttpMessage, stream: BufferedIOBase):
    for b in msg.to_bytes():
        stream.write(b)
    stream.write(b"\r\n")


def serialize_message_pair(rr: RequestResponse, stream: BufferedIOBase):
    stream.write(b"Pair: ")
    stream.write(str(rr.guid.hex).encode())
    stream.write(b"\r\n")

    if rr.request:
        stream.write(b"Request: ")
        serialize_message(rr.request, stream)
    else:
        stream.write(b"NoRequest\r\n")

    if rr.response:
        stream.write(b"Response: ")
        serialize_message(rr.response, stream)
    else:
        stream.write(b"NoResponse\r\n")


def serialize_message_pairs(pairs, stream: BufferedIOBase):
    for pair in pairs:
        serialize_message_pair(pair, stream)


def parse_message_pair(data):
    kw, data = yield from get_word(data)
    assert kw == b"Pair:"
    uuid_str, data = yield from get_word(data)
    rr = RequestResponse()
    rr.guid = UUID(hex=uuid_str.decode())

    kw, data = yield from get_word(data)
    if kw == b"Request:":
        rr.request, data = yield from get_http_request(data)
        _, data = yield from get_line(data)  # Read the newline

    kw, data = yield from get_word(data)
    if kw == b"Response:":
        rr.response, data = yield from get_http_request(data)
        _, data = yield from get_line(data)  # Read the newline

    return rr, data


def parse_message_pairs(stream: BufferedIOBase):
    parser = intialize_parser(parse_message_pair)

    data = stream.read(1024)
    while data:
        for rr in parse(parser, data):
            yield rr
        data = stream.read(1024)
