"""Configuration constants and minimal ABIs for interacting with Curve USDC/crvUSD.

This module keeps addresses, defaults, and ABIs centralized so the main script
can focus on flow control.
"""

from __future__ import annotations

DEFAULT_RPC_URL = "http://127.0.0.1:8545"
ENV_RPC_URL = "RPC_URL"
ENV_IMPERSONATED_ADDRESS = "IMPERSONATED_ADDRESS"
ENV_BURN_BPS = "BURN_BPS"

POOL_ADDRESS = "0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# Use a 1% slippage buffer against the estimated output.
SLIPPAGE_BPS = 99
MAX_COINS_CHECK = 4
MIN_BURN_BPS = 1
MAX_BURN_BPS = 10_000

# Minimal ERC-20 ABI (USDC)
ERC20_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Minimal ABI for the Curve USDC/crvUSD pool (which is also the LP token)
CURVE_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "i", "type": "uint256"}],
        "name": "coins",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_burn_amount", "type": "uint256"},
            {"internalType": "int128", "name": "i", "type": "int128"},
        ],
        "name": "calc_withdraw_one_coin",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_burn_amount", "type": "uint256"},
            {"internalType": "int128", "name": "i", "type": "int128"},
            {"internalType": "uint256", "name": "_min_received", "type": "uint256"},
        ],
        "name": "remove_liquidity_one_coin",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_burn_amount", "type": "uint256"},
            {"internalType": "int128", "name": "i", "type": "int128"},
            {"internalType": "uint256", "name": "_min_received", "type": "uint256"},
            {"internalType": "address", "name": "_receiver", "type": "address"},
        ],
        "name": "remove_liquidity_one_coin",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

