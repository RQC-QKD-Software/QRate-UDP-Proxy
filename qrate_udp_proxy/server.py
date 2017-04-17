# ~*~ coding: utf-8 ~*~

import threading
import socket
import platform
import logging
import binascii

from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TSSLSocket import TSSLSocket
from thrift.transport.TTransport import TBufferedTransport

from qkd_client_api.v1.QkdApiService import Client
from qkd_client_api.v1 import ttypes

import proto


SOCKET_TIMEOUT = 3


class QRateUDPAPI(object):
    def __init__(self, bind_ip, bind_port, reply_port,
                 qrate_ip, qrate_port, certfile, keyfile, ca_certs,
                 *args, **kwargs):
        self.__log = logging.getLogger("QRateUDPAPI")

        self.__request_recv_socket = socket.socket(socket.AF_INET,
                                                 socket.SOCK_DGRAM)
        self.__request_recv_socket.settimeout(SOCKET_TIMEOUT)
        self.__request_recv_socket.bind((bind_ip, bind_port))
        if platform.system() != 'Darwin':
            self.__request_recv_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 256)
        self.__log.debug("Listening for requests on {}:{}".format(
            bind_ip, bind_port))

        self.__reply_send_socket = socket.socket(socket.AF_INET,
                                                 socket.SOCK_DGRAM)
        self.__reply_send_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__reply_send_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__reply_port = reply_port

        thrift_transport = TBufferedTransport(TSSLSocket(
            qrate_ip, qrate_port, validate=False,
            certfile=certfile, keyfile=keyfile, ca_certs=ca_certs))
        self.__qrate_api_client = Client(TBinaryProtocol(thrift_transport))
        thrift_transport.open()

        self.__stop_event = threading.Event()
        self.__request_processing_thread = threading.Thread(
            target=self.__request_processing_loop)

    def __send_error_reply(self, ip_addr, command_magic, error_code,
                           retry_after=0.0, error_message=None):
        if error_message is None:
            error_message = ""

        self.__reply_send_socket.sendto(
            b''.join((
                proto.Reply.from_fields(
                    system_magic=proto.SYSTEM_MAGIC,
                    command_magic=command_magic,
                    result_code=error_code).as_data(),
                proto.ErrorDescription.from_fields(
                    retry_after=retry_after).as_data(),
                error_message[:proto.ERROR_MESSAGE_LENGTH_MAX])),
            (ip_addr, self.__reply_port))

    def __handle_client_error(self, addr, request, exc):
        self.__log.warning("Client error {} on get_by_length(): {}".format(
            exc.error_code, exc.message))
        self.__send_error_reply(addr[0], request.command_magic, exc.error_code,
                                error_message=exc.message)

    def __handle_server_error(self, addr, request, exc):
        self.__log.warning("Server error {} on get_by_length(): {} "
                           "Retry after {}".format(
            exc.error_code, exc.message, exc.retry_after))
        self.__send_error_reply(
            addr[0], request.command_magic, exc.error_code,
            retry_after=exc.retry_after, error_message=exc.message)

    def __handle_request(self, addr, request, data):
        if request.system_magic != proto.SYSTEM_MAGIC:
            self.__log.warning("Got packet with wrong system magic")
            return

        if request.command_code == proto.CMD_GET_KEY_BY_LENGTH:
            key_length = proto.KeyByLengthRequest.unpack(data).key_length
            self.__log.info("Request key by length {}".format(key_length))
            key_data = self.__qrate_api_client.get_by_length(key_length)
            self.__log.info("Got key from QRate Thrift API")
            self.__reply_send_socket.sendto(
                b''.join((
                    proto.Reply.from_fields(
                        system_magic=proto.SYSTEM_MAGIC,
                        command_magic=request.command_magic,
                        result_code=proto.RESULT_CODE_SUCCESS).as_data(),
                    proto.KeyByLengthReply.from_fields(
                        key_id=key_data.key_id,
                        expiration_time=key_data.expiration_time).as_data(),
                    key_data.key_body[:proto.KEY_LENGTH_MAX])),
                (addr[0], self.__reply_port))
            self.__log.info("Sent Reply with key")
        elif request.command_code == proto.CMD_GET_KEY_BY_ID:
            key_id = proto.KeyByIdRequest.unpack(data).key_id
            self.__log.info("Request key by id {}".format(
                binascii.hexlify(key_id)))
            key_data = self.__qrate_api_client.get_by_id(key_id)
            self.__log.info("Got key from QRate Thrift API")
            self.__reply_send_socket.sendto(
                b''.join((
                    proto.Reply.from_fields(
                        system_magic=proto.SYSTEM_MAGIC,
                        command_magic=request.command_magic,
                        result_code=proto.RESULT_CODE_SUCCESS).as_data(),
                    key_data.key_body[:proto.KEY_LENGTH_MAX])),
                (addr[0], self.__reply_port))
            self.__log.info("Sent Reply with key")
        else:
            self.__log.warning("Got wrong command code {}".format(
                request.command_code))

    def __request_processing_loop(self):
        while not self.__stop_event.is_set():
            try:
                data, addr = self.__request_recv_socket.recvfrom(
                    proto.RECV_PACKET_SIZE)
            except socket.error as e:
                self.__log.debug("No data received for {} seconds ({})".format(
                    SOCKET_TIMEOUT, e))
                continue

            self.__log.info("Got packet from {}:{}".format(addr[0], addr[1]))

            if len(data) < proto.Request.struct.size:
                self.__log.warning("Got packet of size {}. It is samaller "
                                   "then minimal packet size {}".format(
                    len(data), proto.Request.struct.size))
                return

            request = proto.Request.unpack(data[:proto.Request.struct.size])

            try:
                self.__handle_request(
                    addr, request, data[proto.Request.struct.size:])
            except ttypes.QkdClientError as exc:
                self.__handle_client_error(addr, request, exc)
            except ttypes.QkdServerError as exc:
                self.__handle_server_error(addr, request, exc)
            except Exception as exc:
                self.__log.warning("Got unexpeted exception {}".format(exc))
                self.__send_error_reply(
                    addr[0], request.command_magic,
                    proto.RESULT_CODE_THRIFT_API_CONNECTION,
                    error_message=str(exc))

    def start(self):
        self.__request_processing_thread.start()

    def stop(self):
        self.__stop_event.set()

        self.__request_processing_thread.join()
