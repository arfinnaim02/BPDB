"""HTTPS client using the operating system's certificate store."""

import ssl

import httpx
import truststore


def create_client(timeout: float = 60) -> httpx.Client:
    return httpx.Client(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "BPDB-Research-Collector/0.2"},
    )