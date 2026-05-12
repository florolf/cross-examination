#!/usr/bin/env python3

import time
from collections import defaultdict

from . import utils
from .tlog import TreeHead, ConsistencyProof, NoteSignature

def parse_ascii(doc: str) -> dict[str, list[list[str]]]:
    out = defaultdict(list)

    for line in doc.splitlines():
        if not line:
            continue

        key, value = line.split('=', 1)
        out[key].append(value.split())

    return out


class SigsumLog:
    def __init__(self, endpoint: str, pubkey: bytes):
        self.endpoint = endpoint
        self.key_hash = utils.sha256(pubkey)
        self.session = utils.make_session()

        self.origin = f"sigsum.org/v1/tree/{self.key_hash.hex()}"
        self.vkey_id = utils.vkey_id(self.origin, 1, pubkey)

    def __str__(self) -> str:
        return f'SigsumLog(endpoint={self.endpoint})'

    def do_request(self, *args, timeout=60) -> str:
        url = '/'.join([self.endpoint, *[str(x) for x in args]])

        backoff = 1
        deadline = time.time() + timeout
        while True:
            remaining = max(0, deadline - time.time())

            resp = self.session.get(url, timeout=remaining)
            if resp.status_code == 429:
                if time.time() + backoff < deadline:
                    time.sleep(backoff)
                    backoff *= 2
                    continue

            resp.raise_for_status()
            return resp.text

    def get_tree_head(self) -> TreeHead:
        ascii_ = self.do_request('get-tree-head')
        data = parse_ascii(ascii_)

        root_hash = bytes.fromhex(data['root_hash'][0][0])
        if len(root_hash) != 32:
            raise ValueError(f'unexpected root_hash length: {len(root_hash)} != 32')

        size = int(data['size'][0][0])
        if size < 0:
            raise ValueError(f'negative tree size: {size}')

        signature = bytes.fromhex(data['signature'][0][0])

        return TreeHead(
            f"sigsum.org/v1/tree/{self.key_hash.hex()}",
            [NoteSignature(self.origin, self.vkey_id, signature)],
            size,
            root_hash)

    def get_consistency_proof(self, old_size: int, new_size: int) -> ConsistencyProof:
        ascii_ = self.do_request('get-consistency-proof', old_size, new_size)
        proof = parse_ascii(ascii_)

        return ConsistencyProof(
            old_size,
            new_size,
            [bytes.fromhex(x[0]) for x in proof['node_hash']]
        )
