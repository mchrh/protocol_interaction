# Curve USDC/crvUSD Single-Sided Withdrawal

Withdraw single-sided USDC liquidity from the Curve USDC/crvUSD factory pool on an Ethereum mainnet fork using Python and `web3.py`. The script impersonates an LP holder, burns a configurable portion of LP tokens, and withdraws only USDC via `remove_liquidity_one_coin`.

- Pool: `0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E`
- USDC: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`

## Prerequisites
- Python 3.10+
- Mainnet RPC key (e.g., Alchemy/Infura) to fork Ethereum mainnet
- A fork tool (e.g., Foundry Anvil recommended)
- Package manager: [`uv`](https://github.com/astral-sh/uv) (preferred). `pip` works too, but instructions below use `uv`.

## Install Foundry / Anvil
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup                 # installs/updates anvil, forge, cast
export PATH="$HOME/.foundry/bin:$PATH"  # add to shell profile for permanence
anvil --version           # verify it runs
```

## Start a Mainnet Fork (Anvil example)
```bash
# 1. Export your mainnet RPC key
export MAINNET_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"

# 2. Start an Anvil fork
anvil --fork-url "$MAINNET_RPC_URL"
```
Anvil exposes RPC at `http://127.0.0.1:8545` and provides several funded test accounts printed in the terminal.

## Installation
```bash
git clone <this-repo-url>
cd <this-repo>

# Create & activate venv with uv
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies via uv (reads requirements.txt)
uv pip install -r requirements.txt
```

## Finding an LP Holder to Impersonate
1. Open the pool token (Curve USDC/crvUSD) on Etherscan or Curve’s UI.
2. View holders for the LP token.
3. Copy an address with a non-trivial LP balance.
4. Use that address for `--impersonated-address`.

**Warning:** Never impersonate real accounts on real mainnet. This is only safe on a local fork.

## Running the Script
Impersonated address used for this project’s examples: `0xf4D898ae2bc5C83E7638DB434f33Dceb8dc7Ab19` (you can swap for any LP holder).
```bash
# Dry run (no tx sent)
uv run python -m src.curve_withdraw \
  --rpc-url http://127.0.0.1:8545 \
  --impersonated-address 0xf4D898ae2bc5C83E7638DB434f33Dceb8dc7Ab19 \
  --burn-bps 100 \
  --dry-run

# Execute withdrawal
uv run python -m src.curve_withdraw \
  --rpc-url http://127.0.0.1:8545 \
  --impersonated-address 0xf4D898ae2bc5C83E7638DB434f33Dceb8dc7Ab19 \
  --burn-bps 100

# Equivalent package entry
uv run python -m src \
  --rpc-url http://127.0.0.1:8545 \
  --impersonated-address 0xf4D898ae2bc5C83E7638DB434f33Dceb8dc7Ab19 \
  --burn-bps 100
```
You should see LP & USDC balances before/after, USDC received (human + raw), tx hash, and `Status: SUCCESS`.

Environment variables (CLI args take precedence):
- `RPC_URL` for `--rpc-url` (default `http://127.0.0.1:8545`)
- `IMPERSONATED_ADDRESS` for `--impersonated-address`
- `BURN_BPS` for `--burn-bps` (default 100 = 1%)
