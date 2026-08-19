import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from models import Allocation


def write_output(
    allocations: list[Allocation],
    output_dir: str,
    source: str,
    network: str | None,
    subnets_considered: int,
    subnets_excluded: int,
    generated_at: datetime | None = None,
) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    timestamp = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_market_cap = sum(
        (allocation.market_cap for allocation in allocations), Decimal("0")
    )

    payload = {
        "generated_at": timestamp,
        "source": source,
        "network": network,
        "subnets_considered": subnets_considered,
        "subnets_excluded": subnets_excluded,
        "total_market_cap": _json_number(total_market_cap),
        "allocations": [_allocation_record(allocation) for allocation in allocations],
    }

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "allocation.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    (output_path / "summary.md").write_text(
        _summary_markdown(
            timestamp=timestamp,
            source=source,
            network=network,
            allocations=allocations,
            subnets_considered=subnets_considered,
            subnets_excluded=subnets_excluded,
        )
    )
    print(_stdout_summary(len(allocations), source, network, allocations))


def _allocation_record(allocation: Allocation) -> dict:
    subnet = allocation.subnet_data
    return {
        "netuid": subnet.netuid,
        "symbol": subnet.symbol,
        "name": subnet.name,
        "price": _json_number(subnet.price),
        "circulating_supply": _json_number(subnet.circulating_supply),
        "market_cap": _json_number(allocation.market_cap),
        "weight": _json_number(allocation.weight),
    }


def _stdout_summary(
    count: int,
    source: str,
    network: str | None,
    allocations: list[Allocation],
) -> str:
    from_clause = f"{source} on {network}" if network else source
    top = allocations[:3]
    if not top:
        return f"Generated 0 allocations from {from_clause}."

    top_weights = ", ".join(
        f"{item.subnet_data.symbol} {item.weight * Decimal('100'):.2f}%"
        for item in top
    )
    return (
        f"Generated {count} allocations from {from_clause}. "
        f"Top {len(top)} weights: {top_weights}."
    )


def _summary_markdown(
    *,
    timestamp: str,
    source: str,
    network: str | None,
    allocations: list[Allocation],
    subnets_considered: int,
    subnets_excluded: int,
) -> str:
    top_ten = allocations[:10]
    rows = "\n".join(
        f"| {item.subnet_data.netuid} | {item.subnet_data.symbol} | "
        f"{item.subnet_data.name} | {_json_number(item.market_cap)} | "
        f"{item.weight:.4f} |"
        for item in top_ten
    ) or "| — | — | — | — | — |"

    assumptions = (
        "Market cap is price times circulating alpha supply. In RPC mode, "
        "circulating supply is derived from SubtensorModule.SubnetAlphaOut "
        "(outstanding alpha). Weights are rounded to 4 decimal places with the "
        "largest-remainder method so they sum to 1.0000. "
        f"{subnets_considered} subnet(s) were considered and {subnets_excluded} "
        "were excluded."
    )

    return (
        "# Bittensor market-weighted allocation\n\n"
        f"- Generated at: {timestamp}\n"
        f"- Source: {source}\n"
        f"- Network: {network if network is not None else 'n/a'}\n\n"
        "## Top 10 allocations\n\n"
        "| netuid | symbol | name | market_cap | weight |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{rows}\n\n"
        "## Assumptions\n\n"
        f"{assumptions}\n"
    )


def _json_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)
