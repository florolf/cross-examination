#!/usr/bin/env python3

import argparse
import logging
import time
import heapq
import json
from pathlib import Path
from typing import Optional

from . import sigsum, tlog, witness


logger = logging.getLogger(__name__)


class Log:
    def __init__(self, api: tlog.LogAPI):
        self.api = api
        self.size = None

    def __str__(self):
        return f'Log(origin={self.api.origin}, size={self.size})'

    def submit(self, witness: witness.Witness) -> Optional[str]:
        th = self.api.get_tree_head()
        # always refresh cosignatures
        #if self.size == th.size:
        #    logger.debug('nothing to do for %s', th.origin)
        #    return None

        if self.size is None or self.size == th.size:
            cp = tlog.ConsistencyProof(th.size, th.size, [])
        else:
            cp = self.api.get_consistency_proof(self.size, th.size)

        result = witness.add_checkpoint(th, cp)
        match result:
            case int():
                actual_size = result
            case str():
                logger.debug('updated witness for %s from %s to %d', th.origin, self.size, th.size)
                self.size = th.size
                return result

        logger.info('got size mismatch for %s, local %s, remote %d', th.origin, self.size, actual_size)
        if actual_size == 0:
            cp = tlog.ConsistencyProof(0, th.size, [])
        else:
            cp = self.api.get_consistency_proof(actual_size, th.size)

        result = witness.add_checkpoint(th, cp)
        if type(result) is not str:
            raise RuntimeError(f'update with refreshed size failed for {th.origin}')

        logger.debug('updated witness for %s from %d to %d', th.origin, actual_size, th.size)
        self.size = th.size

        return result


class ScheduleEntry:
    def __init__(self, log: Log, interval: int):
        self.log = log
        self.interval = interval
        self.next = 0

    def schedule(self, now: int) -> None:
        self.next = now + self.interval

    def __lt__(self, other: ScheduleEntry) -> bool:
        return self.next < other.next

    def __str__(self) -> str:
        return f'ScheduleEntry(log={str(self.log)}, interval={self.interval}, next={self.next})'


def parse_config(path: Path) -> list[tuple[int, Log]]:
    logs: list[tuple[int, Log]] = []

    with path.open('r') as f:
        for line in f:
            line = line.strip()

            if line.startswith('#'):
                continue

            interval, *log_def = line.split()
            match log_def:
                case ['sigsum', url, keyhash]:
                    log = Log(sigsum.SigsumLog(url, bytes.fromhex(keyhash)))
                case _:
                    logger.error(f'unsupported log type {log_def[0]}')
                    continue

            logs.append((int(interval), log))

    return logs


def main() -> None:
    parser = argparse.ArgumentParser(prog="cross-examination", description="Transparency log checkpoint forwarder")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--cosignatures", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("witness", type=str, help='witness base URL')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    w = witness.Witness(args.witness)

    cosignatures = {}

    logs = []
    for interval, log in parse_config(args.config):
        logs.append(ScheduleEntry(log, interval))

    now = time.time()
    for entry in logs:
        entry.next = now

    heapq.heapify(logs)

    while True:
        now = time.time()

        entry = heapq.heappop(logs)
        if now < entry.next:
            time.sleep(entry.next - now)

        try:
            result = entry.log.submit(w)
            if result is not None:
                cosignatures[entry.log.api.origin] = [entry.log.size, result]
        except Exception as e:
            logging.error('updating log %s failed', entry.log, exc_info=e)

        if args.cosignatures is not None:
            try:
                args.cosignatures.write_text(
                    json.dumps(cosignatures, sort_keys=True, indent=True)
                )
            except:
                pass

        entry.schedule(time.time())
        heapq.heappush(logs, entry)

if __name__ == "__main__":
    main()
