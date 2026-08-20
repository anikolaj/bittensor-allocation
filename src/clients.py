import json
import bittensor as bt
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

from models import SubnetData, SubnetDataResult


class SubnetClient(ABC):
    @abstractmethod
    def get_subnet_data(self) -> SubnetDataResult:
        ...


class BittensorSubnetClient(SubnetClient):
    def __init__(self, network: str):
        self.network = network

    def get_subnet_data(self) -> SubnetDataResult:
        subtensor = bt.Subtensor(network=self.network)
        subnet_infos = subtensor.subnets.all()
        symbols = subtensor.subnets.token_symbols()
        names = subtensor.subnets.subnet_names()
        prices = subtensor.prices.alpha_prices()
        alpha_out_rows = subtensor.query_map(bt.storage.SubtensorModule.SubnetAlphaOut)
        circulating_supplies = {
            int(netuid): bt.Balance.from_rao(int(amount or 0), int(netuid)).decimal
            for netuid, amount in alpha_out_rows
        }

        subnet_data: list[SubnetData] = []
        for subnet_info in subnet_infos:
            netuid = int(subnet_info.netuid)
            # Missing price or outstanding alpha is an exclusion. A value that
            # exists but cannot be converted to Decimal is treated as fatal.
            if netuid not in prices or netuid not in circulating_supplies:
                continue

            symbol = str(symbols.get(netuid, f"SN{netuid}"))
            subnet_data.append(
                SubnetData(
                    netuid=netuid,
                    symbol=symbol,
                    name=str(names.get(netuid, symbol)),
                    price=self._to_decimal(prices[netuid]),
                    circulating_supply=self._to_decimal(circulating_supplies[netuid]),
                )
            )

        return SubnetDataResult(
            subnets=subnet_data,
            subnets_considered=len(subnet_infos),
            subnets_excluded=len(subnet_infos) - len(subnet_data),
        )

    def _to_decimal(self, value: object) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int | float | str):
            return Decimal(str(value))

        for attr_name in ("tao",):
            attr_value = getattr(value, attr_name, None)
            if attr_value is not None:
                return Decimal(str(attr_value))

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise RuntimeError(f"Unable to convert chain value {value!r} to Decimal") from exc


class FixtureSubnetClient(SubnetClient):
    REQUIRED_FIELDS = ("netuid", "symbol", "name", "price", "circulating_supply")

    def __init__(self, input_path: str):
        self.input_path = input_path

    def get_subnet_data(self) -> SubnetDataResult:
        try:
            with open(self.input_path) as f:
                payload = json.load(f)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise ValueError(f"Unable to read fixture file: {self.input_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Fixture file is not valid JSON: {self.input_path}") from exc

        if not isinstance(payload, list):
            raise ValueError(
                f"Fixture file must contain a JSON array of subnet objects: {self.input_path}"
            )

        subnet_data: list[SubnetData] = []
        excluded = 0
        for item in payload:
            parsed = self._parse_subnet(item)
            if parsed is None:
                excluded += 1
                continue
            subnet_data.append(parsed)

        return SubnetDataResult(
            subnets=subnet_data,
            subnets_considered=len(payload),
            subnets_excluded=excluded,
        )

    def _parse_subnet(self, item: object) -> SubnetData | None:
        """Return SubnetData for a valid row, or None to exclude incomplete/malformed rows."""
        if not isinstance(item, dict):
            return None
        if any(field not in item for field in self.REQUIRED_FIELDS):
            return None

        try:
            return SubnetData(
                netuid=int(item["netuid"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                price=Decimal(str(item["price"])),
                circulating_supply=Decimal(str(item["circulating_supply"])),
            )
        except (InvalidOperation, TypeError, ValueError):
            return None

