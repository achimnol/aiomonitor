import argparse
import shutil
import struct
import telnetlib

from .monitor import MONITOR_HOST, MONITOR_PORT


def opt_callback(sock, command, option):
    if command == telnetlib.DO and option == telnetlib.TTYPE:
        sock.sendall(b''.join([
            telnetlib.IAC,
            telnetlib.WILL,
            telnetlib.TTYPE,
            telnetlib.IAC,
            telnetlib.SB,
            telnetlib.TTYPE,
            telnetlib.BINARY,
            b"unknown",  # "raw" terminal
            telnetlib.IAC,
            telnetlib.SE,
        ]))
    elif command == telnetlib.DO and option == telnetlib.NAWS:
        term_size = shutil.get_terminal_size()
        sock.sendall(b''.join([
            telnetlib.IAC,
            telnetlib.WILL,
            telnetlib.NAWS,
            telnetlib.IAC,
            telnetlib.SB,
            telnetlib.NAWS,
            struct.pack('>HH', term_size.columns, term_size.lines),
            telnetlib.IAC,
            telnetlib.SE,
        ]))
    elif command == telnetlib.DO and option == telnetlib.LINEMODE:
        sock.sendall(b''.join([
            telnetlib.IAC,
            telnetlib.WONT,
            telnetlib.LINEMODE,
        ]))
    elif command == telnetlib.DO and option == telnetlib.CHARSET:
        sock.sendall(b''.join([
            telnetlib.IAC,
            telnetlib.WILL,
            telnetlib.CHARSET,
            telnetlib.IAC,
            telnetlib.SB,
            telnetlib.CHARSET,
            b"en_US.ASCII",
            telnetlib.IAC,
            telnetlib.SE,
        ]))


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
