"""Single-sided USDC withdrawal from the Curve USDC/crvUSD pool on a mainnet fork.

The script impersonates an LP holder on a local fork (e.g., Anvil), burns a
configurable portion of their LP tokens, and withdraws only USDC via
`remove_liquidity_one_coin`. All interactions are against the real mainnet
contracts on a fork—never mainnet directly.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Dict, Tuple

from dotenv import load_dotenv
from rich.console import Console
from web3 import HTTPProvider, Web3
from web3.contract import Contract
from web3.exceptions import BadFunctionCallOutput, ContractLogicError

import src.config as config

console = Console()


@dataclass
class Balances:
    lp_balance: int
    usdc_balance: int
    lp_decimals: int
    usdc_decimals: int
    usdc_symbol: str


def parse_args(argv: list[str] | None = None, env: Dict[str, str] | os._Environ[str] = os.environ) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Burn Curve USDC/crvUSD LP tokens and withdraw USDC on a mainnet fork.",
    )
    parser.add_argument(
        "--rpc-url",
        default=env.get(config.ENV_RPC_URL, config.DEFAULT_RPC_URL),
        help=f"RPC URL of the local fork (default: {config.DEFAULT_RPC_URL} or ${config.ENV_RPC_URL})",
    )
    parser.add_argument(
        "--impersonated-address",
        default=env.get(config.ENV_IMPERSONATED_ADDRESS),
        help="Address of a Curve USDC/crvUSD LP holder to impersonate (or set ${}).".format(
            config.ENV_IMPERSONATED_ADDRESS
        ),
    )
    parser.add_argument(
        "--burn-bps",
        type=int,
        default=int(env.get(config.ENV_BURN_BPS, 100)),
        help="Basis points of the LP balance to burn (default: 100 = 1%%). Range: {}-{}".format(
            config.MIN_BURN_BPS, config.MAX_BURN_BPS
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only estimate outputs and print balances without sending a transaction.",
    )
    args = parser.parse_args(argv)

    if not args.impersonated_address:
        parser.error("Missing --impersonated-address (or set ${}).".format(config.ENV_IMPERSONATED_ADDRESS))

    if not (config.MIN_BURN_BPS <= args.burn_bps <= config.MAX_BURN_BPS):
        parser.error(f"--burn-bps must be between {config.MIN_BURN_BPS} and {config.MAX_BURN_BPS}.")

    return args


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit(f"Failed to connect to RPC at {rpc_url}. Is your local fork running?")
    return w3


def to_checksum(w3: Web3, address: str) -> str:
    try:
        return w3.to_checksum_address(address)
    except ValueError as exc:
        sys.exit(f"Invalid Ethereum address provided: {address}. Error: {exc}")


def impersonate_and_fund(w3: Web3, impersonated: str, funding_account: str, fund_eth: float = 0.1) -> None:
    """Impersonate the LP holder on a local fork and optionally top up gas.

    Impersonation is only safe on a fork; never attempt this against real mainnet.
    """
    resp = w3.provider.make_request("anvil_impersonateAccount", [impersonated])
    if resp.get("error"):
        sys.exit(f"RPC error during impersonation: {resp['error']}")

    # Provide a small ETH balance so the impersonated account can pay gas.
    tx = {
        "from": funding_account,
        "to": impersonated,
        "value": w3.to_wei(fund_eth, "ether"),
    }
    w3.eth.send_transaction(tx)
    console.print(f"[green]Impersonation successful[/green]; funded {fund_eth} ETH from {funding_account} to {impersonated}.")


def get_usdc_index(pool: Contract, usdc_address: str) -> int:
    for i in range(config.MAX_COINS_CHECK):
        try:
            coin_addr = pool.functions.coins(i).call()
        except (BadFunctionCallOutput, ContractLogicError):
            break
        if Web3.to_checksum_address(coin_addr) == Web3.to_checksum_address(usdc_address):
            return i
    sys.exit(f"Cannot find USDC in pool coins(); expected {config.USDC_ADDRESS}.")


def read_balances(pool: Contract, usdc: Contract, address: str) -> Balances:
    lp_balance = pool.functions.balanceOf(address).call()
    usdc_balance = usdc.functions.balanceOf(address).call()
    lp_decimals = pool.functions.decimals().call()
    usdc_decimals = usdc.functions.decimals().call()
    usdc_symbol = usdc.functions.symbol().call()
    return Balances(
        lp_balance=lp_balance,
        usdc_balance=usdc_balance,
        lp_decimals=lp_decimals,
        usdc_decimals=usdc_decimals,
        usdc_symbol=usdc_symbol,
    )


def format_units(amount: int, decimals: int) -> str:
    return f"{amount / (10 ** decimals):,.6f}"


def calc_burn_amount(lp_balance: int, burn_bps: int) -> int:
    burn_amount = lp_balance * burn_bps // config.MAX_BURN_BPS
    if burn_amount == 0:
        sys.exit(
            "Computed burn amount is zero; LP position may be too small for the requested --burn-bps."
        )
    return burn_amount


def estimate_usdc(pool: Contract, burn_amount: int, usdc_index: int) -> int:
    expected = pool.functions.calc_withdraw_one_coin(burn_amount, usdc_index).call()
    if expected == 0:
        sys.exit("calc_withdraw_one_coin suggests 0 output; burn amount may be too small or pool is imbalanced.")
    return expected


def withdraw_one_coin(
    w3: Web3, pool: Contract, burn_amount: int, usdc_index: int, min_received: int, receiver: str
) -> Tuple[str, dict]:
    tx_hash = pool.functions.remove_liquidity_one_coin(
        burn_amount, usdc_index, min_received, receiver
    ).transact({"from": receiver})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        sys.exit(f"Transaction failed (status {receipt.status}). Hash: {tx_hash.hex()}")
    return tx_hash.hex(), dict(receipt)


def log_dry_run(
    rpc_url: str,
    pool_address: str,
    impersonated: str,
    balances: Balances,
    burn_amount: int,
    usdc_index: int,
    expected_usdc: int,
    min_received: int,
) -> None:
    console.print("[bold yellow]=== Dry Run: Curve USDC/crvUSD Single-Sided Withdrawal ===[/bold yellow]")
    console.print(f"RPC URL: {rpc_url}")
    console.print(f"Pool: {pool_address}")
    console.print(f"Impersonated address: {impersonated}")
    console.print()
    console.print(f"LP balance: {format_units(balances.lp_balance, balances.lp_decimals)} LP (raw: {balances.lp_balance})")
    console.print(f"Burn amount: {format_units(burn_amount, balances.lp_decimals)} LP (raw: {burn_amount})")
    console.print()
    console.print(f"USDC balance: {format_units(balances.usdc_balance, balances.usdc_decimals)} {balances.usdc_symbol} (raw: {balances.usdc_balance})")
    console.print(f"USDC index in pool: {usdc_index}")
    console.print(f"USDC decimals: {balances.usdc_decimals}")
    console.print(
        f"Expected USDC from calc_withdraw_one_coin: {format_units(expected_usdc, balances.usdc_decimals)} {balances.usdc_symbol} (raw: {expected_usdc})"
    )
    console.print(
        f"Min received constraint (slippage buffer {config.SLIPPAGE_BPS}%): {format_units(min_received, balances.usdc_decimals)} {balances.usdc_symbol} (raw: {min_received})"
    )


def log_result(
    rpc_url: str,
    pool_address: str,
    impersonated: str,
    before: Balances,
    after: Balances,
    burn_amount: int,
    lp_burned: int,
    usdc_received: int,
    expected_usdc: int,
    min_received: int,
    tx_hash: str,
) -> None:
    console.print("[bold green]=== Curve USDC/crvUSD Single-Sided Withdrawal ===[/bold green]")
    console.print(f"RPC URL: {rpc_url}")
    console.print(f"Pool: {pool_address}")
    console.print(f"Impersonated address: {impersonated}")
    console.print()
    console.print(f"LP balance before: {format_units(before.lp_balance, before.lp_decimals)} LP (raw: {before.lp_balance})")
    console.print(f"LP burned:        {format_units(lp_burned, before.lp_decimals)} LP (raw: {lp_burned})")
    console.print(f"LP balance after: {format_units(after.lp_balance, after.lp_decimals)} LP (raw: {after.lp_balance})")
    console.print()
    console.print(
        f"USDC balance before: {format_units(before.usdc_balance, before.usdc_decimals)} {before.usdc_symbol} (raw: {before.usdc_balance})"
    )
    console.print(
        f"USDC balance after:  {format_units(after.usdc_balance, after.usdc_decimals)} {after.usdc_symbol} (raw: {after.usdc_balance})"
    )
    console.print(
        f"USDC received:       {format_units(usdc_received, after.usdc_decimals)} {after.usdc_symbol} (raw: {usdc_received})"
    )
    console.print()
    console.print(
        f"Expected USDC from calc_withdraw_one_coin: {format_units(expected_usdc, before.usdc_decimals)} {before.usdc_symbol}"
    )
    console.print(
        f"Min received constraint (slippage buffer {config.SLIPPAGE_BPS}%): {format_units(min_received, before.usdc_decimals)} {before.usdc_symbol}"
    )
    console.print()
    console.print(f"Tx hash: {tx_hash}")
    console.print("[bold green]Status: SUCCESS[/bold green]")


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    args = parse_args(argv)
    rpc_url = args.rpc_url

    w3 = get_web3(rpc_url)
    impersonated = to_checksum(w3, args.impersonated_address)
    pool_address = to_checksum(w3, config.POOL_ADDRESS)
    usdc_address = to_checksum(w3, config.USDC_ADDRESS)

    if not w3.eth.accounts:
        sys.exit("No local accounts found; ensure your fork tool exposes funded accounts.")
    funding_account = w3.eth.accounts[0]

    pool = w3.eth.contract(address=pool_address, abi=config.CURVE_POOL_ABI)
    usdc = w3.eth.contract(address=usdc_address, abi=config.ERC20_ABI)

    impersonate_and_fund(w3, impersonated, funding_account)

    usdc_index = get_usdc_index(pool, usdc_address)

    balances_before = read_balances(pool, usdc, impersonated)
    if balances_before.lp_balance == 0:
        sys.exit(f"LP balance is zero for address {impersonated}; please select another LP holder.")

    burn_amount = calc_burn_amount(balances_before.lp_balance, args.burn_bps)
    expected_usdc = estimate_usdc(pool, burn_amount, usdc_index)
    min_received = expected_usdc * config.SLIPPAGE_BPS // 100

    if args.dry_run:
        log_dry_run(
            rpc_url,
            pool_address,
            impersonated,
            balances_before,
            burn_amount,
            usdc_index,
            expected_usdc,
            min_received,
        )
        return

    w3.eth.default_account = impersonated
    tx_hash, _receipt = withdraw_one_coin(
        w3, pool, burn_amount, usdc_index, min_received, impersonated
    )

    balances_after = read_balances(pool, usdc, impersonated)
    lp_burned = balances_before.lp_balance - balances_after.lp_balance
    usdc_received = balances_after.usdc_balance - balances_before.usdc_balance

    log_result(
        rpc_url,
        pool_address,
        impersonated,
        balances_before,
        balances_after,
        burn_amount,
        lp_burned,
        usdc_received,
        expected_usdc,
        min_received,
        tx_hash,
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        # Allow argparse and explicit sys.exit to propagate.
        raise
    except Exception:
        console.print("[red]Unexpected error occurred[/red]")
        console.print(traceback.format_exc())
        sys.exit(1)
