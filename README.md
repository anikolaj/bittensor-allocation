# Bittensor Market-Weighted Allocation

CLI that connects to Bittensor (or a local fixture), builds a ranked subnet
universe, and writes a market-weighted allocation list.

Python 3.11+ and `bittensor==11.1.0`.

## Layout

```text
src/                 # application code
tests/               # pytest suite
fixtures/subnets.json
output/              # runtime output (gitignored) + checked-in samples
```

## RPC mode

Live chain data from the Bittensor SDK:

```bash
uv sync
uv run python src/main.py --mode rpc --network finney
```

Requires network access to the `finney` RPC endpoint. Writes
`output/allocation.json` and `output/summary.md`.

## Fixture mode

No chain access. Uses `fixtures/subnets.json`:

```bash
uv sync
uv run python src/main.py --mode fixture --input ./fixtures/subnets.json
```

## Tests

```bash
uv sync --group dev
uv run pytest
```

## Docker

```bash
docker build -t submission .
docker run submission --mode fixture --input ./fixtures/subnets.json
```

That fixture run does not need live chain access. It writes
`output/allocation.json` and `output/summary.md` inside the container and
prints a one-line summary to stdout.

To copy the files out of the container:

```bash
docker run --rm -v "$PWD/output:/app/output" submission --mode fixture --input ./fixtures/subnets.json
```

Sample fixture output is checked in as `output/allocation.sample.json` and
`output/summary.sample.md`.

## Assumptions

- `market_cap = price * circulating_supply`
- `weight = market_cap / total_market_cap`, rounded to 4 decimals, with any
  rounding remainder applied to the largest market-cap allocation so weights
  sum to `1.0000`
- Results are sorted by descending market cap (ties by `netuid`)
- In RPC mode, circulating supply is `SubtensorModule.SubnetAlphaOut`
  (outstanding alpha, not pool reserve `SubnetAlphaIn`)
- `subnets_considered` is the number of subnets the client examined
- `subnets_excluded` is how many of those were dropped for missing price or
  outstanding-alpha data (RPC), or for incomplete/malformed fixture rows
- Malformed RPC numeric values raise rather than counting as exclusions
- Invalid fixture JSON or a non-array root fails with a clear error; bad rows
  inside an otherwise valid fixture are skipped and counted as excluded

## AI Usage

See [AI_USAGE.md](AI_USAGE.md) for details on the AI tools used during development and how their output was verified.
