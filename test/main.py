# ~*~ coding: utf-8 ~*~

import argparse
import socket
import platform

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from qrate_udp_proxy import proto


SOCKET_TIMEOUT = 3


def handle_error(result_code, data):
    error_description = proto.ErrorDescription.unpack(
        data[:proto.ErrorDescription.struct.size])
    error_string = data[proto.ErrorDescription.struct.size:]

    assert False, "Got error {}: {} Retry after {}".format(
        result_code, error_string, error_description.retry_after)


def handle_key_by_length_reply(data):
    key_id = proto.KeyByLengthReply.unpack(
        data[:proto.KeyByLengthReply.struct.size]).key_id
    key = data[proto.KeyByLengthReply.struct.size:]

    return key_id, key


def handle_key_by_id_reply(data):
    return data


def handle_reply(handler, command_magic, data):
    assert len(data) >= proto.Reply.struct.size, \
           "Packet must be at least of size {}".format(
                proto.Reply.struct.size)

    reply = proto.Reply.unpack(data[:proto.Reply.struct.size])

    assert reply.system_magic == proto.SYSTEM_MAGIC
    assert reply.command_magic == command_magic

    payload = data[proto.Reply.struct.size:]
    result_code = reply.result_code
    if result_code >= 0:
        return handler(payload)
    else:
        handle_error(result_code, payload)


def get_key_by_length(qrate_sock, reply_sock, command_magic, key_length):
    qrate_sock.send(b''.join((
        proto.Request.from_fields(
            system_magic=proto.SYSTEM_MAGIC,
            command_magic=command_magic,
            command_code=proto.CMD_GET_KEY_BY_LENGTH).as_data(),
        proto.KeyByLengthRequest.from_fields(
            key_length=key_length).as_data())))

    data = reply_sock.recv(proto.RECV_PACKET_SIZE)

    return handle_reply(handle_key_by_length_reply, command_magic, data)


def get_key_by_id(qrate_sock, reply_sock, command_magic, key_id):
    qrate_sock.send(b''.join((
        proto.Request.from_fields(
            system_magic=proto.SYSTEM_MAGIC,
            command_magic=command_magic,
            command_code=proto.CMD_GET_KEY_BY_ID).as_data(),
        proto.KeyByIdRequest.from_fields(
            key_id=key_id).as_data())))

    data = reply_sock.recv(proto.RECV_PACKET_SIZE)

    return handle_reply(handle_key_by_id_reply, command_magic, data)


def create_send_socket(addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.connect(addr)
    return sock


def create_recv_sock(addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(SOCKET_TIMEOUT)
    sock.bind(addr)
    if platform.system() != 'Darwin':
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 256)
    return sock


def main():
    description = """
        QRate UDP API client example. Performs requests by length and by id on
        both sides: Tx and Rx.
    """

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--qrate-udp-ip-tx', default="127.0.0.1", metavar="ADDRESS",
        help="IP address of UDP API on Tx side")
    parser.add_argument(
        '--qrate-udp-port-tx', default=proto.PORT_REQUEST, metavar="PORT",
        type=int, help="Port of UDP API on Tx side")
    parser.add_argument(
        '--qrate-udp-ip-rx', default="127.0.0.1",  metavar="ADDRESS",
        help="IP address of UDP API on Rx side")
    parser.add_argument(
        '--qrate-udp-port-rx', default=proto.PORT_REQUEST, metavar="PORT",
        type=int, help="Port of UDP API on Tx side")
    parser.add_argument('--reply-ip', default="0.0.0.0",  metavar="ADDRESS",
                        help="Bind IP address for listening for Reply")
    parser.add_argument(
        '--reply-port', default=proto.PORT_REPLY, type=int, metavar="PORT",
        help="Bind port for listening for Reply")
    parser.add_argument('-l', '--key-length', default=1384, type=int,
                        help="Key length for request by length")
    args = parser.parse_args()

    tx_sock = create_send_socket(
        (args.qrate_udp_ip_tx, args.qrate_udp_port_tx))
    rx_sock = create_send_socket(
        (args.qrate_udp_ip_rx, args.qrate_udp_port_rx))
    reply_sock = create_recv_sock((args.reply_ip, args.reply_port))

    command_magic_tx = 0
    command_magic_rx = 0

    key_id, tx_key = get_key_by_length(
        tx_sock, reply_sock, command_magic_tx, args.key_length)
    rx_key = get_key_by_id(rx_sock, reply_sock, command_magic_rx, key_id)

    assert(tx_key == rx_key)

    command_magic_tx += 1
    command_magic_rx += 1

    key_id, rx_key = get_key_by_length(
        rx_sock, reply_sock, command_magic_rx, args.key_length)
    tx_key = get_key_by_id(tx_sock, reply_sock, command_magic_tx, key_id)

    assert(tx_key == rx_key)

    print "Test passed"


if __name__ == "__main__":
    main()
