import json
from datetime import datetime, timezone
from decimal import Decimal

from models import Allocation, SubnetData
from output import write_output

REQUIRED_ROOT_FIELDS = {
    "generated_at",
    "source",
    "network",
    "subnets_considered",
    "subnets_excluded",
    "total_market_cap",
    "allocations",
}
REQUIRED_ALLOCATION_FIELDS = {
    "netuid",
    "symbol",
    "name",
    "price",
    "circulating_supply",
    "market_cap",
    "weight",
}
FIXED_TIME = datetime(2026, 3, 10, 18, 0, 0, tzinfo=timezone.utc)


def allocation(
    netuid: int,
    *,
    symbol: str | None = None,
    name: str | None = None,
    price: str,
    circulating_supply: str,
    market_cap: str,
    weight: str,
) -> Allocation:
    symbol = symbol or f"SN{netuid}"
    return Allocation(
        subnet_data=SubnetData(
            netuid=netuid,
            symbol=symbol,
            name=name or f"Subnet {netuid}",
            price=Decimal(price),
            circulating_supply=Decimal(circulating_supply),
        ),
        market_cap=Decimal(market_cap),
        weight=Decimal(weight),
    )


def write(
    tmp_path,
    allocations: list[Allocation],
    *,
    source="rpc",
    network="finney",
    subnets_considered=None,
    subnets_excluded=0,
    generated_at=FIXED_TIME,
):
    write_output(
        allocations,
        str(tmp_path),
        source,
        network,
        len(allocations) if subnets_considered is None else subnets_considered,
        subnets_excluded,
        generated_at,
    )
    return tmp_path / "allocation.json", tmp_path / "summary.md"


def test_allocation_json_exists(tmp_path):
    json_path, _ = write(tmp_path, [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")])

    assert json_path.is_file()


def test_allocation_json_has_required_fields(tmp_path):
    json_path, _ = write(
        tmp_path,
        [allocation(1, price="12.34", circulating_supply="10000", market_cap="123400", weight="1.0000")],
    )
    payload = json.loads(json_path.read_text())

    assert REQUIRED_ROOT_FIELDS <= payload.keys()
    assert REQUIRED_ALLOCATION_FIELDS <= payload["allocations"][0].keys()


def test_decimal_values_become_json_numbers(tmp_path):
    json_path, _ = write(
        tmp_path,
        [allocation(1, price="12.34", circulating_supply="10000", market_cap="123400", weight="0.1000")],
        subnets_considered=1,
    )
    raw = json_path.read_text()
    payload = json.loads(raw)
    record = payload["allocations"][0]

    assert '"price": 12.34' in raw
    assert '"circulating_supply": 10000' in raw
    assert '"market_cap": 123400' in raw
    assert '"weight": 0.1' in raw
    assert isinstance(record["price"], float)
    assert isinstance(record["circulating_supply"], int)
    assert isinstance(record["market_cap"], int)
    assert isinstance(record["weight"], float)
    assert isinstance(payload["total_market_cap"], int)


def test_weights_are_represented_correctly(tmp_path):
    json_path, _ = write(
        tmp_path,
        [
            allocation(1, price="1", circulating_supply="50", market_cap="50", weight="0.5000"),
            allocation(2, price="1", circulating_supply="30", market_cap="30", weight="0.3000"),
            allocation(3, price="1", circulating_supply="20", market_cap="20", weight="0.2000"),
        ],
    )
    weights = [item["weight"] for item in json.loads(json_path.read_text())["allocations"]]

    assert weights == [0.5, 0.3, 0.2]
    assert sum(weights) == 1.0


def test_summary_md_exists(tmp_path):
    _, summary_path = write(
        tmp_path,
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
    )

    assert summary_path.is_file()


def test_summary_includes_top_10(tmp_path):
    allocations = [
        allocation(
            netuid,
            price="1",
            circulating_supply=str(100 - netuid),
            market_cap=str(100 - netuid),
            weight="0.0001",
        )
        for netuid in range(1, 13)
    ]
    _, summary_path = write(tmp_path, allocations)
    summary = summary_path.read_text()

    assert "## Top 10 allocations" in summary
    for netuid in range(1, 11):
        assert f"| {netuid} | SN{netuid} |" in summary
    assert "| 11 | SN11 |" not in summary
    assert "| 12 | SN12 |" not in summary


def test_stdout_has_expected_rpc_format(tmp_path, capsys):
    write(
        tmp_path,
        [
            allocation(1, symbol="SN1", price="1", circulating_supply="10", market_cap="10", weight="0.1000"),
            allocation(4, symbol="SN4", price="1", circulating_supply="8", market_cap="8", weight="0.0873"),
            allocation(12, symbol="SN12", price="1", circulating_supply="7", market_cap="7", weight="0.0791"),
        ],
    )

    assert capsys.readouterr().out == (
        "Generated 3 allocations from rpc on finney. "
        "Top 3 weights: SN1 10.00%, SN4 8.73%, SN12 7.91%.\n"
    )


def test_stdout_fixture_format_omits_network(tmp_path, capsys):
    write(
        tmp_path,
        [allocation(1, symbol="SN1", price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
        source="fixture",
        network=None,
    )

    assert capsys.readouterr().out == (
        "Generated 1 allocations from fixture. Top 1 weights: SN1 100.00%.\n"
    )


def test_stdout_empty_allocations(tmp_path, capsys):
    write(tmp_path, [], subnets_considered=0)

    assert capsys.readouterr().out == "Generated 0 allocations from rpc on finney.\n"


def test_generated_at_uses_injected_timestamp(tmp_path):
    json_path, summary_path = write(
        tmp_path,
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
    )

    assert json.loads(json_path.read_text())["generated_at"] == "2026-03-10T18:00:00Z"
    assert "- Generated at: 2026-03-10T18:00:00Z" in summary_path.read_text()


def test_json_preserves_source_network_and_counts(tmp_path):
    json_path, _ = write(
        tmp_path,
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
        source="rpc",
        network="finney",
        subnets_considered=128,
        subnets_excluded=2,
    )
    payload = json.loads(json_path.read_text())

    assert payload["source"] == "rpc"
    assert payload["network"] == "finney"
    assert payload["subnets_considered"] == 128
    assert payload["subnets_excluded"] == 2


def test_json_network_is_null_when_missing(tmp_path):
    json_path, summary_path = write(
        tmp_path,
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
        source="fixture",
        network=None,
    )

    assert json.loads(json_path.read_text())["network"] is None
    assert "- Source: fixture" in summary_path.read_text()
    assert "- Network: n/a" in summary_path.read_text()


def test_total_market_cap_is_sum_of_allocations(tmp_path):
    json_path, _ = write(
        tmp_path,
        [
            allocation(1, price="1", circulating_supply="10", market_cap="10.5", weight="0.5000"),
            allocation(2, price="1", circulating_supply="10", market_cap="10.25", weight="0.5000"),
        ],
    )

    assert json.loads(json_path.read_text())["total_market_cap"] == 20.75


def test_allocation_order_is_preserved(tmp_path):
    json_path, _ = write(
        tmp_path,
        [
            allocation(9, price="1", circulating_supply="1", market_cap="1", weight="0.5000"),
            allocation(2, price="1", circulating_supply="1", market_cap="1", weight="0.5000"),
        ],
    )

    assert [item["netuid"] for item in json.loads(json_path.read_text())["allocations"]] == [9, 2]


def test_summary_reports_considered_and_excluded(tmp_path):
    _, summary_path = write(
        tmp_path,
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
        subnets_considered=128,
        subnets_excluded=2,
    )
    summary = summary_path.read_text()

    assert "128 subnet(s) were considered and 2 were excluded." in summary
    assert "SubtensorModule.SubnetAlphaOut" in summary


def test_creates_output_directory(tmp_path):
    output_dir = tmp_path / "nested" / "out"
    write_output(
        [allocation(1, price="1", circulating_supply="10", market_cap="10", weight="1.0000")],
        str(output_dir),
        "rpc",
        "finney",
        1,
        0,
        FIXED_TIME,
    )

    assert (output_dir / "allocation.json").is_file()
    assert (output_dir / "summary.md").is_file()
