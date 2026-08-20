# AI Usage

I used ChatGPT and Cursor during development as my primary AI tools.

## ChatGPT

I used ChatGPT to:
- reason about the project architecture and module boundaries
- understand Bittensor subnet data and alpha supply
- review the Bittensor SDK integration
- design and review allocation logic
- review tests and edge cases
- review the final implementation against the challenge specification

## Cursor

I used Cursor to:
- generate initial implementations and tests
- inspect Bittensor SDK APIs
- iterate on the client and output implementations
- add docker functionality for containerization
- analyze code for mistakes, edge cases, and any missing requirements

## Verification

I did not treat AI-generated code as authoritative. I verified the implementation by:
- checking the Bittensor SDK behavior directly against the installed `bittensor==11.1.0` package
- catching incorrect SDK assumptions from early AI suggestions — for example, `Subtensor.all_subnets()` and `metagraph.alpha_out` do not exist in 11.1.0; the working path is `subtensor.subnets.all()` for enumeration and `SubtensorModule.SubnetAlphaOut` for outstanding alpha supply
- mocking RPC responses in unit tests
- testing allocation edge cases
- testing malformed and incomplete inputs
- running the fixture mode without network access
- running the application through Docker
- reviewing the final implementation against the challenge requirements