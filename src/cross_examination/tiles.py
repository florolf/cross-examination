import typing
from collections import OrderedDict
from typing import Self, Optional

from pathlib import Path

from . import utils
from .tlog import TreeHead, NoteSignature, ConsistencyProof
from .utils import b64dec, sha256


def split(n: int) -> int:
    assert n > 1

    if n & (n-1) == 0:
        k = n >> 1
    else:
        k = 1 << (n.bit_length() - 1)

    return k


class Tile:
    def __init__(self, hashes: list[bytes]):
        if len(hashes) > 256:
            raise ValueError(f'tile too large: {len(hashes)}')

        self.hashes = hashes

    @property
    def length(self):
        return len(self.hashes)

    def __getitem__(self, index):
        return self.hashes[index]

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        if len(data) % 32:
            raise ValueError('tile data needs to be a multiple of 32 bytes')

        return cls([data[i:i+32] for i in range(0, len(data), 32)])


class TilesBackend(typing.Protocol):
    def get(self, *path: str) -> Optional[bytes]:
        ...


class LocalBackend:
    def __init__(self, base: Path):
        self.base = base

    def get(self, *path: str) -> Optional[bytes]:
        p = self.base.joinpath(*path)
        try:
            return p.read_bytes()
        except FileNotFoundError:
            return None


class HttpBackend:
    def __init__(self, base: str):
        self.base = base.rstrip('/')
        self.session = utils.make_session()

    def get(self, *path: str) -> Optional[bytes]:
        url = self.base + '/' + '/'.join(path)
        result = self.session.get(url)
        result.raise_for_status()

        return result.content


class TileCache:
    def __init__(self):
        self.tiles: OrderedDict[tuple[int, int], Tile] = OrderedDict()
        self.max_size = 32

    def get(self, l: int, n: int) -> Optional[Tile]:
        key = (l, n)
        if key not in self.tiles:
            return None

        self.tiles.move_to_end(key)
        return self.tiles[key]

    def put(self, l: int, n: int, tile: Tile) -> None:
        key = (l, n)
        self.tiles[key] = tile
        self.tiles.move_to_end(key)

        while len(self.tiles) > self.max_size:
            self.tiles.popitem(last=False)


class Tiles:
    def __init__(self, origin: str, backend: TilesBackend):
        self.backend = backend
        self.origin = origin
        self.size = None
        self.tile_cache = TileCache()

    def _get_tile(self, l: int, n: int, partial: int = 0) -> Optional[Tile]:
        elements = ['%03d' % (n % 1000)]
        while n >= 1000:
            n //= 1000
            elements.insert(0, 'x%03d' % (n % 1000))

        if partial:
            elements[-1] += '.p'
            elements.append('%d' % partial)

        path = ['tile', str(l), *elements]
        data = self.backend.get(*path)
        if data is None:
            return None

        return Tile.from_bytes(data)

    def _get_from_tile(self, l: int, n: int, i: int) -> bytes:
        cached_tile = self.tile_cache.get(l, n)
        if cached_tile is not None and cached_tile.length > i:
            return cached_tile[i]

        level_entries = self.size // 256**l
        current_tile, current_partial_size = divmod(level_entries, 256)

        tile = None
        if n == current_tile:
            tile = self._get_tile(l, n, current_partial_size)
        if tile is None:
            tile = self._get_tile(l, n)

        if tile is None:
            raise RuntimeError(f'could not get tile at L={l}, N={n}')

        if cached_tile is None or tile.length > cached_tile.length:
            self.tile_cache.put(l, n, tile)

        return tile[i]

    def get_tree_head(self) -> TreeHead:
        data = self.backend.get('checkpoint')
        if data is None:
            raise RuntimeError('no checkpoint found')

        cp = data.decode()
        lines = cp.splitlines()

        if len(lines) < 4:
            raise ValueError('expected at least 4 lines in checkpoint, got: %s' % lines)

        if lines[3] != '':
            raise ValueError('expected blank in line 4, got: %s' % lines)

        signatures = [NoteSignature.from_line(x) for x in lines[4:]]
        self.size = int(lines[1])

        origin = lines[0]
        if origin != self.origin:
            raise RuntimeError(f'unexpected origin, got "{origin}", wanted "{self.origin}"')

        return TreeHead(origin, signatures, self.size, b64dec(lines[2]))

    @staticmethod
    def mth_in_tile(start: int, end: int) -> Optional[tuple[int, int, int]]:
        l = 0
        while start & 0xff == 0 and end & 0xff == 0:
            start >>= 8
            end >>= 8
            l += 1

        n, i = divmod(start, 256)

        if end != start+1:
            return None

        return l, n, i

    def mth(self, start: int, end: int) -> bytes:
        assert self.size is not None
        assert 0 <= start <= end <= self.size

        size = end - start
        if size == 0:
            return sha256(b'')

        tile_coord = self.mth_in_tile(start, end)
        if tile_coord is not None:
            return self._get_from_tile(*tile_coord)

        k = split(size)
        return sha256(b'\x01' + self.mth(start, start + k) + self.mth(start + k, end))

    def get_consistency_proof(self, old_size: int, new_size: int) -> ConsistencyProof:

        def subproof(m: int, start: int, size: int, b: bool) -> list[bytes]:
            if m == size:
                return [] if b else [self.mth(start, start+size)]
            k = split(size)
            if m <= k:
                return subproof(m, start, k, b) + [self.mth(start + k, start + size)]
            else:
                return subproof(m - k, start + k, size - k, False) + [self.mth(start, start + k)]

        return ConsistencyProof(
            old_size, new_size,
            subproof(old_size, 0, new_size, True)
        )
