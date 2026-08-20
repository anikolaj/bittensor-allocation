from dataclasses import dataclass
from decimal import Decimal


@dataclass
class SubnetData:
    netuid: int
    symbol: str
    name: str
    price: Decimal
    circulating_supply: Decimal


@dataclass
class SubnetDataResult:
    subnets: list[SubnetData]
    subnets_considered: int
    subnets_excluded: int


@dataclass
class Allocation:
    subnet_data: SubnetData
    market_cap: Decimal
    weight: Decimal
