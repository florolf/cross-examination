import hashlib
import base64

import requests

from .__about__ import VERSION as CROSS_EXAMINATION_VERSION


def b64enc(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def b64dec(text: str) -> bytes:
    return base64.b64decode(text)


def sha256(data: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(data)
    return h.digest()


def vkey_id(name: str, sig_type: int, pubkey: bytes) -> int:
    return int.from_bytes(sha256(
        name.encode() +
        b'\n' +
        sig_type.to_bytes() +
        pubkey
    )[:4])


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers['User-Agent'] = f'cross-examination/{CROSS_EXAMINATION_VERSION}'

    return session
