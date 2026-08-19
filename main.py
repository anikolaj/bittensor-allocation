import argparse

from allocation import calculate_allocations
from clients import BittensorSubnetClient, FixtureSubnetClient
from output import write_output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a market-weighted allocation across Bittensor subnets."
    )
    parser.add_argument(
        "--mode",
        choices=["rpc", "fixture"],
        required=True,
        help="Data source: live Bittensor RPC or a local fixture file.",
    )
    parser.add_argument(
        "--network",
        type=str,
        help="Bittensor network name (e.g. finney). Used in RPC mode.",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to a subnet fixture JSON file. Used in fixture mode.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    print("Running bittensor-allocation!")
    print(f"mode={args.mode} network={args.network} input={args.input}")

    if args.mode == "rpc":
        client = BittensorSubnetClient(args.network)
    elif args.mode == "fixture":
        client = FixtureSubnetClient(args.input)
    else:
        raise ValueError(f"Invalid mode: {args.mode}")

    result = client.get_subnet_data()
    allocations = calculate_allocations(result.subnets)
    write_output(
        allocations,
        ".",
        source=args.mode,
        network=args.network,
        subnets_considered=result.subnets_considered,
        subnets_excluded=result.subnets_excluded,
    )


if __name__ == "__main__":
    main()

