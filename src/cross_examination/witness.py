#!/usr/bin/env python3

import logging

from . import utils
from .tlog import TreeHead, ConsistencyProof
from .utils import b64enc


logger = logging.getLogger(__name__)


class Witness:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.session = utils.make_session()

    def add_checkpoint(self, th: TreeHead, cp: ConsistencyProof) -> int|str:
        body = ''

        body += f'old {cp.old_size}\n'
        body += ''.join([b64enc(node) + '\n' for node in cp.node_hashes])
        body += '\n'

        body += th.serialize()

        resp = self.session.post(self.endpoint + '/add-checkpoint', body)
        if resp.status_code == 409 and resp.headers['Content-Type'] == 'text/x.tlog.size':
            return int(resp.text)

        resp.raise_for_status()

        return resp.text.strip()
