from __future__ import annotations

import ssl
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CERT_PATH = BASE_DIR / "cert.pem"
KEY_PATH = BASE_DIR / "key.pem"


def create_server_ssl_context(
    cert_path: Path = CERT_PATH,
    key_path: Path = KEY_PATH,
) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    return context


def create_test_client_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
