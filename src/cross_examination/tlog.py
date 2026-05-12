from dataclasses import dataclass
from typing import Protocol

from .utils import b64enc

@dataclass(frozen=True)
class NoteSignature:
    name: str
    key_id: int
    payload: bytes

    def __str__(self) -> str:
        return f"NoteSignature(name={self.name}, key_id={self.key_id}, payload={self.payload.hex()})"

    def serialize(self) -> str:
        return f'\u2014 {self.name} {b64enc(self.key_id.to_bytes(4) + self.payload)}'

@dataclass(frozen=True)
class TreeHead:
    origin: str
    signatures: list[NoteSignature]

    size: int
    root_hash: bytes

    def __str__(self):
        signatures = [str(x) for x in self.signatures]
        return f"TreeHead(size={self.size}, root_hash={self.root_hash.hex()}, signatures={','.join(signatures)})"

    def serialize(self) -> str:
        checkpoint = f"{self.origin}\n{self.size}\n{b64enc(self.root_hash)}\n\n"

        for sig in self.signatures:
            checkpoint += f'{sig.serialize()}\n'

        return checkpoint


@dataclass(frozen=True)
class ConsistencyProof:
    old_size: int
    new_size: int

    node_hashes: list[bytes]

    def __str__(self):
        hashes = ", ".join([x.hex() for x in self.node_hashes])
        return f"ConsistencyProof(old_size={self.old_size}, new_size={self.new_size}, node_hashes=[{hashes}]"


class LogAPI(Protocol):
    def get_tree_head(self) -> TreeHead:
        ...

    def get_consistency_proof(self, old_size: int, new_size: int) -> ConsistencyProof:
        ...
