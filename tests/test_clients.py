import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import bittensor as bt

from clients import BittensorSubnetClient, FixtureSubnetClient
from models import SubnetData

RAO_PER_ALPHA = 1_000_000_000


def write_fixture(path, rows: list[dict]) -> str:
    path.write_text(json.dumps(rows))
    return str(path)


def fake_subtensor(
    *,
    netuids: list[int],
    prices: dict[int, float],
    alpha_out: dict[int, int],
    symbols: dict[int, str] | None = None,
    names: dict[int, str] | None = None,
) -> MagicMock:
    subtensor = MagicMock()
    subtensor.subnets.all.return_value = [
        SimpleNamespace(netuid=netuid) for netuid in netuids
    ]
    subtensor.subnets.token_symbols.return_value = symbols or {}
    subtensor.subnets.subnet_names.return_value = names or {}
    subtensor.prices.alpha_prices.return_value = prices
    subtensor.query_map.return_value = list(alpha_out.items())
    return subtensor


def test_fixture_client_loads_subnets(tmp_path):
    path = write_fixture(
        tmp_path / "subnets.json",
        [
            {
                "netuid": 1,
                "symbol": "SN1",
                "name": "Apex",
                "price": "12.34",
                "circulating_supply": "10000",
            },
            {
                "netuid": 4,
                "symbol": "SN4",
                "name": "Targon",
                "price": 8.73,
                "circulating_supply": 9000,
            },
        ],
    )

    result = FixtureSubnetClient(path).get_subnet_data()

    assert result.subnets == [
        SubnetData(
            netuid=1,
            symbol="SN1",
            name="Apex",
            price=Decimal("12.34"),
            circulating_supply=Decimal("10000"),
        ),
        SubnetData(
            netuid=4,
            symbol="SN4",
            name="Targon",
            price=Decimal("8.73"),
            circulating_supply=Decimal("9000"),
        ),
    ]


def test_fixture_client_reports_considered_count(tmp_path):
    path = write_fixture(
        tmp_path / "subnets.json",
        [
            {
                "netuid": 1,
                "symbol": "SN1",
                "name": "Apex",
                "price": "1",
                "circulating_supply": "10",
            },
            {
                "netuid": 2,
                "symbol": "SN2",
                "name": "Beta",
                "price": "2",
                "circulating_supply": "20",
            },
            {
                "netuid": 3,
                "symbol": "SN3",
                "name": "Gamma",
                "price": "3",
                "circulating_supply": "30",
            },
        ],
    )

    result = FixtureSubnetClient(path).get_subnet_data()

    assert result.subnets_considered == 3
    assert len(result.subnets) == 3


def test_fixture_client_reports_zero_excluded(tmp_path):
    path = write_fixture(
        tmp_path / "subnets.json",
        [
            {
                "netuid": 1,
                "symbol": "SN1",
                "name": "Apex",
                "price": "1",
                "circulating_supply": "10",
            }
        ],
    )

    result = FixtureSubnetClient(path).get_subnet_data()

    assert result.subnets_excluded == 0


def test_fixture_client_empty_file(tmp_path):
    path = write_fixture(tmp_path / "subnets.json", [])

    result = FixtureSubnetClient(path).get_subnet_data()

    assert result.subnets == []
    assert result.subnets_considered == 0
    assert result.subnets_excluded == 0


def test_fixture_client_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        FixtureSubnetClient(str(tmp_path / "missing.json")).get_subnet_data()


def test_fixture_client_invalid_json_raises(tmp_path):
    path = tmp_path / "subnets.json"
    path.write_text("{not-json")

    with pytest.raises(ValueError, match="not valid JSON"):
        FixtureSubnetClient(str(path)).get_subnet_data()


def test_fixture_client_non_array_raises(tmp_path):
    path = write_fixture(tmp_path / "subnets.json", {"netuid": 1})

    with pytest.raises(ValueError, match="JSON array"):
        FixtureSubnetClient(path).get_subnet_data()


def test_fixture_client_incomplete_row_is_excluded(tmp_path):
    path = write_fixture(
        tmp_path / "subnets.json",
        [
            {
                "netuid": 1,
                "symbol": "SN1",
                "name": "Apex",
                "price": "1",
                "circulating_supply": "10",
            },
            {"netuid": 2, "symbol": "SN2"},
        ],
    )

    result = FixtureSubnetClient(path).get_subnet_data()

    assert [subnet.netuid for subnet in result.subnets] == [1]
    assert result.subnets_considered == 2
    assert result.subnets_excluded == 1


def test_fixture_client_malformed_numeric_value_is_excluded(tmp_path):
    path = write_fixture(
        tmp_path / "subnets.json",
        [
            {
                "netuid": 1,
                "symbol": "SN1",
                "name": "Apex",
                "price": "1",
                "circulating_supply": "10",
            },
            {
                "netuid": 2,
                "symbol": "SN2",
                "name": "Broken",
                "price": "abc",
                "circulating_supply": "10",
            },
        ],
    )

    result = FixtureSubnetClient(path).get_subnet_data()

    assert [subnet.netuid for subnet in result.subnets] == [1]
    assert result.subnets_considered == 2
    assert result.subnets_excluded == 1


def test_fixture_client_non_object_row_is_excluded(tmp_path):
    path = tmp_path / "subnets.json"
    path.write_text(json.dumps([{"netuid": 1, "symbol": "SN1", "name": "Apex", "price": "1", "circulating_supply": "10"}, "bad"]))

    result = FixtureSubnetClient(str(path)).get_subnet_data()

    assert len(result.subnets) == 1
    assert result.subnets_considered == 2
    assert result.subnets_excluded == 1


@patch("clients.bt.Subtensor")
def test_rpc_client_passes_network(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[],
        prices={},
        alpha_out={},
    )

    BittensorSubnetClient("finney").get_subnet_data()

    mock_subtensor_cls.assert_called_once_with(network="finney")


@patch("clients.bt.Subtensor")
def test_rpc_client_queries_subnet_alpha_out(mock_subtensor_cls):
    subtensor = fake_subtensor(netuids=[], prices={}, alpha_out={})
    mock_subtensor_cls.return_value = subtensor

    BittensorSubnetClient("finney").get_subnet_data()

    subtensor.query_map.assert_called_once_with(bt.storage.SubtensorModule.SubnetAlphaOut)


@patch("clients.bt.Subtensor")
def test_rpc_valid_subnet_maps_to_subnet_data(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[1],
        prices={1: 12.34},
        alpha_out={1: 2 * RAO_PER_ALPHA},
        symbols={1: "SN1"},
        names={1: "Apex"},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert result.subnets == [
        SubnetData(
            netuid=1,
            symbol="SN1",
            name="Apex",
            price=Decimal("12.34"),
            circulating_supply=Decimal("2"),
        )
    ]
    assert result.subnets_considered == 1
    assert result.subnets_excluded == 0


@patch("clients.bt.Subtensor")
def test_rpc_missing_price_is_excluded(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[1],
        prices={},
        alpha_out={1: RAO_PER_ALPHA},
        symbols={1: "SN1"},
        names={1: "Apex"},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert result.subnets == []
    assert result.subnets_considered == 1
    assert result.subnets_excluded == 1


@patch("clients.bt.Subtensor")
def test_rpc_missing_alpha_supply_is_excluded(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[1],
        prices={1: 12.34},
        alpha_out={},
        symbols={1: "SN1"},
        names={1: "Apex"},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert result.subnets == []
    assert result.subnets_considered == 1
    assert result.subnets_excluded == 1


@patch("clients.bt.Subtensor")
def test_rpc_mixed_valid_and_excluded_counts(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[1, 2, 3],
        prices={1: 1.5, 3: 2.5},
        alpha_out={1: RAO_PER_ALPHA, 2: 3 * RAO_PER_ALPHA},
        symbols={1: "SN1", 2: "SN2", 3: "SN3"},
        names={1: "Apex", 2: "Beta", 3: "Gamma"},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert [subnet.netuid for subnet in result.subnets] == [1]
    assert result.subnets_considered == 3
    assert result.subnets_excluded == 2


@patch("clients.bt.Subtensor")
def test_rpc_defaults_symbol_and_name_when_missing(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[7],
        prices={7: 1.0},
        alpha_out={7: RAO_PER_ALPHA},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert result.subnets[0].symbol == "SN7"
    assert result.subnets[0].name == "SN7"


@patch("clients.bt.Subtensor")
def test_rpc_empty_universe(mock_subtensor_cls):
    mock_subtensor_cls.return_value = fake_subtensor(
        netuids=[],
        prices={},
        alpha_out={},
    )

    result = BittensorSubnetClient("finney").get_subnet_data()

    assert result.subnets == []
    assert result.subnets_considered == 0
    assert result.subnets_excluded == 0
