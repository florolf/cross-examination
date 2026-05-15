# cross-examination

Modern transparency log implementations like [Sigsum](https://sigsum.org) or [Tessera](https://github.com/transparency-dev/tessera) favor a push-based architecture where the log actively contacts witnesses to collect cosignatures for checkpoints and publishes them together with the checkpoint. This works well, but depends on the log operator configuring a particular set of witnesses.

This is in contrast to earlier designs like [omniwitness](https://github.com/transparency-dev/witness/tree/main/cmd/omniwitness), which primarily uses a pull-based model where witnesses fetch checkpoints and consistency proofs from logs themselves (and distributing them through some other mechanism, like [distributor](https://github.com/transparency-dev/distributor)).

Generally, the push-based model works well, but when you want to have a witness cosign a log (for example because you want to reference it in a trust policy or just as a method to cheaply keep track of a logs good behavior) that isn't configured by the log operator for whatever reason, you're stuck.

`cross-examination` is a small tool that bridges both Sigsum and [tlog-tiles](https://github.com/C2SP/C2SP/blob/main/tlog-tiles.md) based log with witnesses implementing [tlog-witness](https://github.com/C2SP/C2SP/blob/main/tlog-witness.md) and expecting push-mode replication.

## Caveat emptor

This mainly exists because it seemed like a fun thing to do and I wanted an excuse to write a tlog-tiles client. It's not necessarily useful for augmenting your trust policy because it is lacking the coordination a synchronous push-based model inherently provides. For example, if your polling interval is low compared to the growth rate of the log, it might take a few attempts to actually get the cosignatures from the synchronous witnesses and the ones fed by this tool to line up.

## Usage:

Install using your favorite Python build tool, e.g. `uv sync`.

Create a configuration file. The syntax is line-based and each line is either:

```
INTERVAL sigsum URL LOG_KEY
```

for Sigsum logs or

```
INTERVAL tiles ORIGIN URL
```

for tlog-tiles based logs. `INTERVAL` is the polling interval in seconds.

For example:

```
30 sigsum https://seasalp.glasklar.is 0ec7e16843119b120377a73913ac6acbc2d03d82432e2c36b841b09a95841f25
30 sigsum https://ginkgo.tlog.mullvad.net f00c159663d09bbda6131ee1816863b6adcacfe80b0b288000b11aba8fe38314
5 tiles arche2026h1.staging.ct.transparency.dev https://storage.googleapis.com/static-ct-staging-arche2026h1-bucket
```

This will poll the sigsum test logs once every 30 seconds and the arche2026h1 staging CT log every five seconds.

Now run the tool:

```
$ .venv/bin/cross-examination -v --cosignatures cosignatures.json config http://127.0.0.1:7380
```

This will start fetching information from the logs and pushing it to the witness instance running at `http://127.0.0.1:7380`. The `-v` argument causes more verbose logging for debugging purposes. `--cosignatures` optionally stores the cosignatures returned by the witness in a JSON file, for example:

```
{
 "log2025-alpha3.rekor.sigstage.dev": [
  4057999,
  "\u2014 remora.n621.de 2net5wAAAABqB6MRl/ISU7fNtVXmLEn3OXqL1DeAlUbYQLENEHLlvq/fGrTOccV6zEHqFWAFFMuYyADwbIGv+3T/ABAsxw46vGU2Aw=="
 ],
 "sigsum.org/v1/tree/44ad38f8226ff9bd27629a41e55df727308d0a1cd8a2c31d3170048ac1dd22a1": [
  44051,
  "\u2014 remora.n621.de 2net5wAAAABqB6MfgJiCVWaSZaHIUqRb0rq3ppq3BwfIWaFeKf3Xz71oRbXfl1PW4mHslm0Prb3tfNFxf3wWnwrQi8cgThh7mOvaBw=="
 ],
 "sigsum.org/v1/tree/c03f05182be9341e33b9edd5f3f8675b08332164640203e743f4285359cace47": [
  2141,
  "\u2014 remora.n621.de 2net5wAAAABqB6MfwfyMzh74YrlyAMHStWFfQn8hvFBWoTFRP6UEoI2wN7b/8AF/yMZRrr+1QpD+DCzIuHn/uCCeE7tU+sVyKMyACA=="
 ]
}
```

