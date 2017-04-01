# Quantum key distribution (QKD) UDP API proxy

This repository contains Python proxy-server that wraps [QRate Thrift API][1] with UDP protocol without SSL.

## Requirements

See [requirements](https://github.com/RQC-QKD-Software/QRate-Client-API#requirements) and [known issues](https://github.com/RQC-QKD-Software/QRate-Client-API#known-issues) sections in [QRate Thrift API repository][1].


## Quick-start guide

- See [UDP protocol documentation](doc/QRate_UDP_API_ru.docx)
- See [example UDP-client](test/main.py)
- Make sure QRate Thrift API server is running
- Make sure you have client SSL-certificates for QRate Thrift API
- Start UDP API proxy-server (one instance for Tx-side and another instance for Rx-side):
   ```bash

   python qrate_udp_proxy/main.py --bind-port 5551 --reply-port 5552 --qrate-port 9090 --certfile ssl/tx_client.crt --keyfile ssl/tx_client.key --log-level debug
   ```
   *See program help for parameter description.*
- Test UDP API proxy-server with example client:
    ```bash

    python test/main.py --qrate-udp-port-tx 5551 --qrate-udp-port-rx 5556
    ```
    *See program help for parameter description.*
- Write you own client :-)

[1]: https://github.com/RQC-QKD-Software/QRate-Client-API
