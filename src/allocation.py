from decimal import ROUND_HALF_UP, Decimal

from models import Allocation, SubnetData

WEIGHT_QUANTUM = Decimal("0.0001")
ZERO_WEIGHT = Decimal("0.0000")
ONE = Decimal("1.0000")


def calculate_allocations(subnet_data: list[SubnetData]) -> list[Allocation]:
    """Calculate market-cap weights, ordered by descending market cap."""
    # Rank by descending market cap so the output order is deterministic.
    # Equal market caps break ties by netuid.
    ranked = sorted(
        (
            (subnet, subnet.price * subnet.circulating_supply)
            for subnet in subnet_data
        ),
        key=lambda item: (-item[1], item[0].netuid),
    )

    # Weights are shares of total market cap. If nothing is eligible, skip
    # division and return zero weights in the same ranked order.
    total_market_cap = sum((market_cap for _, market_cap in ranked), Decimal("0"))
    if total_market_cap <= 0:
        return [
            Allocation(
                subnet_data=subnet,
                market_cap=market_cap,
                weight=ZERO_WEIGHT,
            )
            for subnet, market_cap in ranked
        ]

    # Round each weight to 4 decimals, then apply any remainder to the
    # largest allocation (ranked[0]) so weights sum to 1.0000.
    weights = [
        (market_cap / total_market_cap).quantize(
            WEIGHT_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        for _, market_cap in ranked
    ]
    remainder = ONE - sum(weights, Decimal("0"))
    if remainder != 0:
        weights[0] += remainder

    return [
        Allocation(
            subnet_data=subnet,
            market_cap=market_cap,
            weight=weight,
        )
        for (subnet, market_cap), weight in zip(ranked, weights)
    ]
