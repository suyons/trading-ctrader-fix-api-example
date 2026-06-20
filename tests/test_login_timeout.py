"""The FIX session must raise (not hang) when login doesn't complete in time.

A stub server accepts the TCP connection on the cTrader QUOTE/TRADE ports but
never sends a logon/security-list reply — the same shape as a closed market or an
unreachable broker. Run with ``uv run pytest``.
"""

import socket
import threading

import pytest

from fix_protocol import FIX_PORTS, FIX

PLAIN_QUOTE_PORT, PLAIN_TRADE_PORT = FIX_PORTS[False]  # 5201, 5202


def _silent_server(port: int, ready: threading.Event, stop: threading.Event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    server.settimeout(0.5)
    ready.set()
    held = []
    while not stop.is_set():
        try:
            conn, _ = server.accept()
            held.append(conn)  # keep the socket open, but never reply
        except socket.timeout:
            continue
    for conn in held:
        conn.close()
    server.close()


def test_login_timeout_raises_instead_of_hanging():
    stop = threading.Event()
    readies = [threading.Event(), threading.Event()]
    servers = [
        threading.Thread(target=_silent_server, args=(port, ready, stop), daemon=True)
        for port, ready in zip((PLAIN_QUOTE_PORT, PLAIN_TRADE_PORT), readies)
    ]
    for thread in servers:
        thread.start()
    for ready in readies:
        assert ready.wait(5), "stub server did not start"

    try:
        with pytest.raises(TimeoutError):
            FIX(
                "127.0.0.1",
                "demo.broker",
                "123",
                "password",
                "USD",
                1,
                lambda *args: None,
                lambda *args: None,
                use_ssl=False,
                login_timeout=2,
            )
    finally:
        stop.set()
        for thread in servers:
            thread.join(timeout=2)
