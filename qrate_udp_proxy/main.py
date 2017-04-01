# ~*~ coding: utf-8 ~*~

import argparse
import logging
import time

import server
import proto


def main():
    description = """
        Proxy server for QRate Thrift API. Main purpose - simplify quantum
        key access. To achieve this goal we implement UDP API wrapper for
        Thrift API and remove SSL.
    """

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--bind-ip', default=proto.BIND_ADDR, metavar="ADDRESS",
        help="Bind IP address for listening for Request")
    parser.add_argument(
        '--bind-port', default=proto.PORT_REQUEST, type=int, metavar="PORT",
        help="Bind port for listening for Request")
    parser.add_argument(
        '--reply-port', default=proto.PORT_REPLY, type=int, metavar="PORT",
        help="Destination port for Reply")
    parser.add_argument('--qrate-ip', default="127.0.0.1", metavar="ADDRESS",
                        help="IP address of QRate Thrift API")
    parser.add_argument('--qrate-port', default=9090, type=int, metavar="PORT",
                        help="Port of QRate Thrift API")
    parser.add_argument('--certfile', default="ssl/client.crt",
                        help="Client x509 certificate")
    parser.add_argument('--keyfile', default="ssl/client.key",
                        help="Client x509 private key")
    parser.add_argument('--ca-certs', default="ssl/pair_ca_bundle.crt",
                        help="Certificate Authority (root or intermediate) "
                             "certificate. Used to authorize API server")
    parser.add_argument('--log-level', default="info",
                        choices=["critical", "error", "warning",
                                 "info", "debug", "notset"],
                        help="Setup output verbosity")
    args = parser.parse_args()

    log_level_dict = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "notset": logging.NOTSET
    }

    logging.basicConfig(level=log_level_dict[args.log_level])

    log = logging.getLogger("QRateUDPProxy")

    qrate_udp_server = server.QRateUDPAPI(
        args.bind_ip, args.bind_port, args.reply_port,
        args.qrate_ip, args.qrate_port,
        args.certfile, args.keyfile, args.ca_certs)

    qrate_udp_server.start()
    log.info("QRate UDP proxy server started")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except KeyboardInterrupt as exc:
        log.warning(exc)

    qrate_udp_server.stop()
    log.info("QRate UDP proxy server stopped")


if __name__ == "__main__":
    main()
