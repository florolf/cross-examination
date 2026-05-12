# cross-examination

Replicate log checkpoints to witnesses by polling.

## Usage:

```
$ uv sync
$ cat > config <<EOF
30 sigsum https://seasalp.glasklar.is 0ec7e16843119b120377a73913ac6acbc2d03d82432e2c36b841b09a95841f25
30 sigsum https://ginkgo.tlog.mullvad.net f00c159663d09bbda6131ee1816863b6adcacfe80b0b288000b11aba8fe38314
EOF
$ .venv/bin/cross-examination -v --cosignatures cosignatures.json config http://127.0.0.1:7380
```

This will poll seasalp and ginkgo every thirty seconds, push the checkpoints to the witness at http://127.0.0.1:7380 and store the resulting cosignatures in `cosignatures.json`.
