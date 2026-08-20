from decimal import ROUND_DOWN, Decimal

from models import Allocation, SubnetData

WEIGHT_SCALE = Decimal("10000")
ZERO_WEIGHT = Decimal("0.0000")


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

    # Largest-remainder method, working in 0.0001 units (x10000).
    # quota is the exact number of units each subnet is owed.
    # units is the truncated whole-unit share; remainders are the leftover
    # fractions used to decide who gets extra units.
    quotas = [
        (market_cap / total_market_cap) * WEIGHT_SCALE
        for _, market_cap in ranked
    ]
    units = [quota.to_integral_value(rounding=ROUND_DOWN) for quota in quotas]
    remainders = [quota - unit for quota, unit in zip(quotas, units)]

    # Truncation usually undershoots 10000 units (1.0000). Give leftover
    # units to the biggest remainders. If it overshoots, take units from
    # the smallest remainders. Ties keep the ranked order above.
    leftover = int(WEIGHT_SCALE - sum(units))
    ranked_indexes = range(len(ranked))
    if leftover > 0:
        recipients = sorted(
            ranked_indexes,
            key=lambda index: (-remainders[index], index),
        )
        for index in recipients[:leftover]:
            units[index] += 1
    elif leftover < 0:
        donors = sorted(
            ranked_indexes,
            key=lambda index: (remainders[index], index),
        )
        for index in donors[: -leftover]:
            units[index] -= 1

    # Convert unit counts back to 4-decimal weights (unit / 10000).
    return [
        Allocation(
            subnet_data=subnet,
            market_cap=market_cap,
            weight=unit / WEIGHT_SCALE,
        )
        for (subnet, market_cap), unit in zip(ranked, units)
    ]
