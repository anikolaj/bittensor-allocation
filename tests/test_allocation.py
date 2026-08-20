from decimal import Decimal

from allocation import calculate_allocations
from models import SubnetData


def subnet(
    netuid: int,
    price: str | int,
    circulating_supply: str | int,
    symbol: str | None = None,
) -> SubnetData:
    return SubnetData(
        netuid=netuid,
        symbol=symbol or f"SN{netuid}",
        name=f"Subnet {netuid}",
        price=Decimal(str(price)),
        circulating_supply=Decimal(str(circulating_supply)),
    )


def test_empty_input_returns_empty_list():
    assert calculate_allocations([]) == []


def test_single_subnet_gets_full_weight():
    allocations = calculate_allocations([subnet(1, price="2", circulating_supply="50")])

    assert len(allocations) == 1
    assert allocations[0].market_cap == Decimal("100")
    assert allocations[0].weight == Decimal("1.0000")


def test_zero_total_market_cap_returns_zero_weights():
    allocations = calculate_allocations(
        [
            subnet(2, price="0", circulating_supply="10"),
            subnet(1, price="5", circulating_supply="0"),
        ]
    )

    assert [item.subnet_data.netuid for item in allocations] == [1, 2]
    assert all(item.weight == Decimal("0.0000") for item in allocations)
    assert all(item.market_cap == Decimal("0") for item in allocations)


def test_results_are_sorted_by_descending_market_cap():
    allocations = calculate_allocations(
        [
            subnet(1, price="2", circulating_supply="5"),
            subnet(2, price="1", circulating_supply="30"),
            subnet(3, price="4", circulating_supply="5"),
        ]
    )

    assert [item.subnet_data.netuid for item in allocations] == [2, 3, 1]
    assert [item.market_cap for item in allocations] == [
        Decimal("30"),
        Decimal("20"),
        Decimal("10"),
    ]
    assert [item.weight for item in allocations] == [
        Decimal("0.5000"),
        Decimal("0.3333"),
        Decimal("0.1667"),
    ]


def test_equal_market_caps_break_ties_by_netuid():
    first = calculate_allocations(
        [
            subnet(5, price="1", circulating_supply="10"),
            subnet(2, price="1", circulating_supply="10"),
        ]
    )
    second = calculate_allocations(
        [
            subnet(2, price="1", circulating_supply="10"),
            subnet(5, price="1", circulating_supply="10"),
        ]
    )

    assert [item.subnet_data.netuid for item in first] == [2, 5]
    assert [item.weight for item in first] == [Decimal("0.5000"), Decimal("0.5000")]
    assert first == second


def test_weights_sum_to_one_and_have_four_decimals():
    allocations = calculate_allocations(
        [
            subnet(1, price="1", circulating_supply="1"),
            subnet(2, price="1", circulating_supply="1"),
            subnet(3, price="1", circulating_supply="1"),
        ]
    )

    weights = [item.weight for item in allocations]
    assert sum(weights) == Decimal("1.0000")
    assert all(weight.as_tuple().exponent == -4 for weight in weights)


def test_rounding_remainder_goes_to_largest_market_cap():
    # Exact weights: A=0.33336, B=0.33335, C=0.33329.
    # Half-up to 4 decimals: 0.3334, 0.3334, 0.3333 (sum 1.0001).
    # Spec: apply the -0.0001 remainder to the largest allocation (A).
    allocations = calculate_allocations(
        [
            subnet(1, price="1", circulating_supply="33336"),
            subnet(2, price="1", circulating_supply="33335"),
            subnet(3, price="1", circulating_supply="33329"),
        ]
    )

    assert [item.subnet_data.netuid for item in allocations] == [1, 2, 3]
    assert allocations[0].weight == Decimal("0.3333")
    assert allocations[1].weight == Decimal("0.3334")
    assert allocations[2].weight == Decimal("0.3333")
    assert sum(item.weight for item in allocations) == Decimal("1.0000")


def test_positive_rounding_remainder_goes_to_largest_market_cap():
    # Three equal caps round to 0.3333 each (sum 0.9999). The +0.0001
    # remainder goes to the first-ranked subnet (lowest netuid on a tie).
    allocations = calculate_allocations(
        [
            subnet(3, price="1", circulating_supply="1"),
            subnet(1, price="1", circulating_supply="1"),
            subnet(2, price="1", circulating_supply="1"),
        ]
    )

    assert [item.subnet_data.netuid for item in allocations] == [1, 2, 3]
    assert allocations[0].weight == Decimal("0.3334")
    assert allocations[1].weight == Decimal("0.3333")
    assert allocations[2].weight == Decimal("0.3333")
    assert sum(item.weight for item in allocations) == Decimal("1.0000")
