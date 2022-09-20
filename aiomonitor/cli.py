import argparse
import os
import shutil
import struct
import sys
import telnetlib

from .monitor import MONITOR_HOST, MONITOR_PORT


def opt_callback(sock, command, option):
    if command == telnetlib.DO and option == b'\x18':  # terminal type
        sock.send(b''.join([
            telnetlib.IAC,
            telnetlib.WILL,
            b'\x18',
            telnetlib.IAC,
            telnetlib.SB,
            b'\x18\x00',
            os.environ.get('TERM', 'xterm').encode('ascii'),
            telnetlib.IAC,
            telnetlib.SE,
        ]))
    elif command == telnetlib.DO and option == b'\x1f':  # window size
        term_size = shutil.get_terminal_size()
        sock.send(b''.join([
            telnetlib.IAC,
            telnetlib.WILL,
            b'\x1f',
            telnetlib.IAC,
            telnetlib.SB,
            b'\x1f',
            struct.pack('>HH', term_size.columns, term_size.lines),
            telnetlib.IAC,
            telnetlib.SE,
        ]))
    else:
        print("OPT_CALLBACK", sock, command, option, file=sys.stderr)


def monitor_client(host: str, port: int) -> None:
    tn = telnetlib.Telnet()
    tn.set_option_negotiation_callback(opt_callback)
    tn.open(host, port, timeout=1)
    try:
        tn.interact()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        tn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-H",
        "--host",
        dest="monitor_host",
        default=MONITOR_HOST,
        type=str,
        help="monitor host ip",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="monitor_port",
        default=MONITOR_PORT,
        type=int,
        help="monitor port number",
    )
    args = parser.parse_args()
    monitor_client(args.monitor_host, args.monitor_port)


if __name__ == "__main__":
    main()
