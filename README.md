# Bittensor Market-Weighted Allocation

CLI that connects to Bittensor (or a local fixture), builds a ranked subnet
universe, and writes a market-weighted allocation list.

Python 3.11+ and `bittensor==11.1.0`.

## RPC mode

Live chain data from the Bittensor SDK:

```bash
uv sync
uv run python main.py --mode rpc --network finney
```

Requires network access to the `finney` RPC endpoint.

## Fixture mode

No chain access. Uses `fixtures/subnets.json`:

```bash
uv sync
uv run python main.py --mode fixture --input ./fixtures/subnets.json
```

## Tests

```bash
uv sync --group dev
uv run pytest
```
