# Spec: Curve USDC/crvUSD Single-Sided USDC Withdrawal on a Mainnet Fork (Python)

This specification is for a coding-oriented assistant (e.g. Codex, Claude Code) that will generate a small Python-based repo.

The repo must:

1. Connect to a **local Ethereum mainnet fork** (e.g. Foundry Anvil).
2. **Impersonate** an LP holder of the Curve **USDC/crvUSD** pool.
3. **Burn LP tokens** from that account on the pool contract
4. **Withdraw only USDC** using `remove_liquidity_one_coin`.
5. Print/log the **USDC received** and updated balances.
6. Include a **README** with clear setup & run instructions.
7. Include a **requirements.txt** listing dependencies.

---

## 1. Protocol & Contract Details (Hard Requirements)

Use the following **fixed contracts** on **Ethereum mainnet**:

- **Curve USDC/crvUSD pool (Factory Plain Pool)**
  - Pool address:  
    `0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E`
  - This **pool contract is also the LP ERC-20 token** (has `balanceOf`, `totalSupply`, `name`, `symbol`, etc.).
  - Important functions to use (from the ABI):
    - `function balanceOf(address) view returns (uint256)`
    - `function totalSupply() view returns (uint256)`
    - `function coins(uint256) view returns (address)`  
    - `function calc_withdraw_one_coin(uint256 _burn_amount, int128 i) view returns (uint256)`
    - Overloads of `remove_liquidity_one_coin`:
      - `function remove_liquidity_one_coin(uint256 _burn_amount, int128 i, uint256 _min_received) returns (uint256)`
      - `function remove_liquidity_one_coin(uint256 _burn_amount, int128 i, uint256 _min_received, address _receiver) returns (uint256)`

- **USDC (Ethereum mainnet)**
  - Token address:  
    `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
  - Standard ERC-20 interface:
    - `function balanceOf(address) view returns (uint256)`
    - `function decimals() view returns (uint8)`
    - `function symbol() view returns (string)`

The script must **not** use any mock contracts. All interactions must be against the **real mainnet contracts** on a fork.

---

## 2. Tech Stack & Tools

### 2.1 Language & Libraries

- **Language**: Python 3.10+ (or latest stable 3.x)
- **Blockchain library**: `web3.py`
  - Use an `HTTPProvider` with the local fork RPC.
- Optional but allowed:
  - `python-dotenv` (for `.env` loading)
  - `rich` or `colorama` for pretty logging

Do **not** use Brownie / Ape as the primary runner (they’re allowed as dependencies only if absolutely needed). Implement the core logic directly with `web3.py`.

### 2.2 Network / Node

- Assume a **local Ethereum mainnet fork**, preferably:
  - **Foundry Anvil** (recommended)
    - e.g.  
      `anvil --fork-url https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY`
- The script must **not** call any public mainnet RPC directly; it must assume it talks to the local fork at e.g. `http://127.0.0.1:8545`.

---

## 3. Repository Layout

Generate the following minimal file structure:

```text
.
├─ README.md
├─ requirements.txt
└─ src/
   ├─ config.py
   ├─ curve_withdraw.py   # main script logic
   └─ __main__.py         # optional: CLI entry for `python -m src`
````

**Notes:**

* `curve_withdraw.py` must expose a `main()` function and a `__name__ == "__main__"` block.
* `config.py` holds constants (addresses, defaults, env var handling, etc.).
* It is acceptable to add additional helper modules under `src/` if useful (e.g. `abi.py`, `utils.py`), but keep it small.

---

## 4. CLI Interface & Configuration

### 4.1 Entry Command

Provide **two equivalent** ways to run:

1. Direct module:

   ```bash
   python -m src.curve_withdraw \
     --rpc-url http://127.0.0.1:8545 \
     --impersonated-address 0x...LPWhale \
     --burn-bps 100
   ```

2. As package entry:

   ```bash
   python -m src \
     --rpc-url http://127.0.0.1:8545 \
     --impersonated-address 0x...LPWhale \
     --burn-bps 100
   ```

Where:

* `--rpc-url`

  * Default: `http://127.0.0.1:8545`
  * Description: URL of the local mainnet fork (Anvil/Hardhat/Ganache).

* `--impersonated-address` (**required**)

  * Address of an account that holds non-zero LP balance for this pool.
  * User will obtain this from Etherscan (any whale or medium holder is fine).

* `--burn-bps` (optional)

  * Integer basis points of the LP position to burn (1 bps = 0.01%).
  * Default: `100` (i.e., burn 1% of the impersonated account’s LP balance).
  * Must be `1 <= burn_bps <= 10_000`.
  * Script must refuse to run if computed burn amount is 0.

* `--dry-run` (optional flag)

  * If set, only prints what it **would** do (balances, estimated USDC via `calc_withdraw_one_coin`) without sending the tx.

Also allow equivalent configuration via environment variables (but CLI args take precedence):

* `RPC_URL` for `--rpc-url`
* `IMPERSONATED_ADDRESS` for `--impersonated-address`
* `BURN_BPS` for `--burn-bps`

---

## 5. Core Behavior

### 5.1 High-Level Flow

The script must:

1. **Parse config**

   * Read CLI args and fall back to environment variables.
   * Validate required inputs and print helpful errors on missing/invalid args.

2. **Connect to RPC**

   * Instantiate `Web3(HTTPProvider(rpc_url))`.
   * Assert connection via `w3.is_connected()`; exit with clear error if not.

3. **Identify a funding account (for gas)**

   * Use `w3.eth.accounts[0]` as the **funding account** (Anvil default).
   * Assumption: On Anvil/Hardhat, this account is unlocked and funded.

4. **Impersonate the LP whale**

   * Call Anvil-specific JSON-RPC:

     ```python
     w3.provider.make_request("anvil_impersonateAccount", [impersonated_address])
     ```
   * Optionally also fund the impersonated address with ETH for gas:

     ```python
     tx = {
       "from": funding_account,
       "to": impersonated_address,
       "value": w3.to_wei(0.1, "ether"),
     }
     w3.eth.send_transaction(tx)
     ```
   * Log that impersonation and funding succeeded.

5. **Instantiate contracts**

   * Pool contract at `0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E`

     * Use a **minimal ABI JSON** embedded in code, containing only required functions (events not required).
   * USDC contract at `0xA0b8...6eB48`

     * Minimal ERC-20 ABI for `balanceOf`, `decimals`, `symbol`.

6. **Discover USDC index in the pool**

   * Programmatically determine which `coins(i)` is USDC:

     * Loop indices `0..3`:

       * For each `i`:

         * `addr = pool.functions.coins(i).call()` inside `try/except`.
         * Stop when call reverts.
       * Compare address (checksum) against USDC address.
     * Raise a descriptive error if USDC is not found.

7. **Read balances before withdrawal**

   * LP balance of impersonated address:

     * `lp_balance = pool.functions.balanceOf(impersonated_address).call()`
   * USDC balance of impersonated address:

     * `usdc_balance_before = usdc.functions.balanceOf(impersonated_address).call()`
   * USDC decimals via `decimals()`, and symbol via `symbol()`.

8. **Determine burn amount**

   * `burn_amount = lp_balance * burn_bps // 10_000`
   * If `burn_amount == 0`, abort with a clear error explaining that the LP position is too small relative to `burn_bps`.
   * Optionally log both raw units and human readable (LP is typically 18 decimals; get via `pool.functions.decimals().call()`).

9. **Estimate expected USDC using `calc_withdraw_one_coin`**

   * `expected_usdc = pool.functions.calc_withdraw_one_coin(burn_amount, usdc_index).call()`
   * Convert to human units for logging using USDC `decimals()`.
   * Set `_min_received` as a conservative fraction, e.g.:

     * `_min_received = expected_usdc * 99 // 100` (1% slippage tolerance).

10. **If `--dry-run`**

    * Print:

      * LP balance
      * Burn amount
      * Expected USDC (raw and human)
      * USDC decimals and symbol
      * USDC index in the pool
    * Exit **without** sending any transaction.

11. **Execute `remove_liquidity_one_coin`**

    * Set `w3.eth.default_account = impersonated_address`.
    * Use 4-argument overload so receiver is explicit:

      ```python
      tx = pool.functions.remove_liquidity_one_coin(
          burn_amount,
          usdc_index,
          min_received,
          impersonated_address,
      ).transact({"from": impersonated_address})
      ```
    * Wait for receipt:

      ```python
      receipt = w3.eth.wait_for_transaction_receipt(tx)
      ```
    * Check `receipt.status == 1`; if not, print revert info if available and fail.

12. **Read balances after withdrawal**

    * `usdc_balance_after = usdc.functions.balanceOf(impersonated_address).call()`
    * `lp_balance_after = pool.functions.balanceOf(impersonated_address).call()`
    * Compute deltas:

      * `usdc_received = usdc_balance_after - usdc_balance_before`
      * `lp_burned = lp_balance - lp_balance_after`

13. **Log results**

    * Print to stdout in a clear, structured format (human-readable + raw integers), for example:

      ```text
      === Curve USDC/crvUSD Single-Sided Withdrawal ===
      RPC URL: http://127.0.0.1:8545
      Pool: 0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E
      Impersonated address: 0x...

      LP balance before:  1234.5678 LP (raw: 1234567800000000000000)
      LP burned:          12.345678 LP (raw: 12345678000000000000)
      LP balance after:   1222.2221 LP (...)

      USDC balance before: 1000.000000 USDC (raw: 1000000000)
      USDC balance after:  1012.345678 USDC (raw: 1012345678)
      USDC received:       12.345678 USDC (raw: 12345678)

      Expected USDC from calc_withdraw_one_coin: 12.40 USDC
      Min received constraint: 12.27 USDC (99% of expected)

      Tx hash: 0x...
      Status: SUCCESS
      ```
    * This logging is **mandatory** to demonstrate the operation worked and to make review easy.

---

## 6. Error Handling Requirements

The script must:

* Exit with **non-zero** exit code on:

  * RPC connection failure
  * Missing required CLI params
  * Zero LP balance on impersonated address
  * Failure to find USDC in `coins(i)`
  * Transaction failure (revert / `receipt.status != 1`)
* Print **clear, actionable** error messages, e.g.:

  * “LP balance is zero for address X; please select another LP holder.”
  * “Cannot find USDC in pool coins(); expected 0xA0b8...6eB48.”
  * “calc_withdraw_one_coin suggests 0 output; pool may be imbalanced or burn amount too small.”
* Catch and log unexpected exceptions with a short stack trace.

---

## 7. Minimal ABIs (Implementation Detail)

The code must embed **minimal ABIs** for:

### 7.1 ERC-20 ABI (USDC)

Only include the subset actually used:

* `balanceOf(address) view returns (uint256)`
* `decimals() view returns (uint8)`
* `symbol() view returns (string)`

### 7.2 Curve Pool ABI (USDC/crvUSD pool)

Only include the subset used:

* `function balanceOf(address) view returns (uint256)`
* `function totalSupply() view returns (uint256)`
* `function decimals() view returns (uint8)`
* `function coins(uint256) view returns (address)`
* `function calc_withdraw_one_coin(uint256, int128) view returns (uint256)`
* `function remove_liquidity_one_coin(uint256, int128, uint256) returns (uint256)`
* `function remove_liquidity_one_coin(uint256, int128, uint256, address) returns (uint256)`

The actual ABI JSON must be syntactically correct and usable by `web3.py`.

---

## 8. README.md Requirements

The generated `README.md` must:

### 8.1 Overview

* Briefly explain:

  * The goal: “Withdraw single-sided USDC liquidity from the Curve USDC/crvUSD factory pool on an Ethereum mainnet fork using Python and web3.py.”
  * The pool and token addresses used.

### 8.2 Prerequisites

* List:

  * Python version requirement.
  * Need for an Ethereum mainnet RPC key (e.g. Alchemy, Infura).
  * Install Foundry or alternative fork tool.

### 8.3 Starting a Mainnet Fork (Example with Anvil)

Include explicit example commands (using the hint):

```bash
# 1. Export your mainnet RPC key
export MAINNET_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"

# 2. Start an Anvil fork
anvil --fork-url "$MAINNET_RPC_URL"
```

Explain that Anvil will:

* Expose RPC at `http://127.0.0.1:8545`
* Provide several funded test accounts printed in the terminal.

### 8.4 Installation

Example section:

```bash
git clone <this-repo-url>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 8.5 Finding an LP Holder to Impersonate

Describe how a reviewer can:

1. Go to the pool on Etherscan or Curve.
2. Navigate to the LP token holdings / holders.
3. Copy an address that has a non-trivial LP balance.
4. Use that address as `--impersonated-address`.

Add a warning:
**Never impersonate real accounts on real mainnet for tx sending. This is only safe on a fork.**

### 8.6 Running the Script

Provide concrete examples:

```bash
# Example: dry run
python -m src.curve_withdraw \
  --rpc-url http://127.0.0.1:8545 \
  --impersonated-address 0xLPWhale... \
  --burn-bps 100 \
  --dry-run

# Example: execute withdrawal
python -m src.curve_withdraw \
  --rpc-url http://127.0.0.1:8545 \
  --impersonated-address 0xLPWhale... \
  --burn-bps 100
```

Explain expected output:

* Shows LP & USDC balances before and after.
* Prints `USDC received` in human-readable form.
* Prints tx hash and confirms `Status: SUCCESS`.

### 8.7 Notes for Other Fork Tools

Mention briefly:

* For **Hardhat** or **Ganache**, the impersonation RPC method may differ:

  * Hardhat: `hardhat_impersonateAccount`
  * Ganache: may require unlocked accounts or private keys.
* The script is written with Anvil in mind; users may adapt the impersonation call accordingly.

---

## 9. requirements.txt

The `requirements.txt` must include at least:

```txt
web3>=6.0.0,<7.0.0
python-dotenv>=1.0.0
```

Optional (nice-to-have):

```txt
rich>=13.0.0
```

Avoid adding heavy or unnecessary dependencies.

---

## 10. Non-Functional Requirements

* Code should be reasonably **clean and commented**:

  * Explain why impersonation is safe here (local fork only).
  * Briefly explain the Curve `remove_liquidity_one_coin` usage.
* Use **type hints** for public functions where straightforward.
* Organize code so that:

  * `main()` is small and orchestrates high-level flow.
  * Helper functions handle:

    * `get_usdc_index(pool, usdc_address)`
    * `impersonate_and_fund(...)`
    * `read_balances(...)`
    * `withdraw_one_coin(...)`

---

## 11. Acceptance Criteria

A reviewer should be able to:

1. Clone the repo and install dependencies using `requirements.txt`.
2. Start an Anvil mainnet fork with their own RPC key.
3. Find an LP whale for the Curve USDC/crvUSD pool using Etherscan.
4. Run the Python script as documented.
5. Observe in the logs:

   * A successful transaction with a hash.
   * Decrease in LP balance of the impersonated address.
   * Increase in USDC balance of the impersonated address.
   * A printed value for “USDC received” that matches the on-chain reality on the fork.

If all the above are true, the implementation satisfies this spec.

```
::contentReference[oaicite:0]{index=0}
```