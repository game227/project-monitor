import socket

from app.process.port_scanner import is_port_in_use


def test_is_port_in_use_detects_bound_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        assert is_port_in_use(port) is True

    assert is_port_in_use(port) is False


def test_is_port_in_use_for_unused_high_port() -> None:
    assert is_port_in_use(59123) is False
