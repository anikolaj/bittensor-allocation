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
    def __init__(self, input: str):
        self.input = input

    def get_subnet_data(self) -> SubnetDataResult:
        with open(self.input) as f:
            payload = json.load(f)

        subnet_data: list[SubnetData] = []
        for item in payload:
            subnet_data.append(
                SubnetData(
                    netuid=int(item["netuid"]),
                    symbol=str(item["symbol"]),
                    name=str(item["name"]),
                    price=Decimal(str(item["price"])),
                    circulating_supply=Decimal(str(item["circulating_supply"])),
                )
            )

        return SubnetDataResult(
            subnets=subnet_data,
            subnets_considered=len(subnet_data),
            subnets_excluded=0,
        )
