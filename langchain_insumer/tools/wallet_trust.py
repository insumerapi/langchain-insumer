"""Tool for generating wallet trust fact profiles."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class WalletTrustSchema(BaseModel):
    """Input for InsumerWalletTrustTool."""

    wallet: str = Field(
        description="EVM wallet address (0x...) to profile.",
    )
    solana_wallet: Optional[str] = Field(
        default=None,
        description="Solana wallet address (base58). Adds the 14-check solana dimension (USDC, EURC, OUSD, PYUSD, USD1, USDG, USDS, BUIDL, USDY, WBTC, cbBTC, tBTC, JitoSOL, mSOL) and lets the institutional EURCV/USDCV on Solana rows evaluate.",
    )
    xrpl_wallet: Optional[str] = Field(
        default=None,
        description="XRPL wallet address (r-address). Adds the xrpl dimension (RLUSD, USDC, OUSG) and lets the institutional EURCV on XRPL row evaluate.",
    )
    bitcoin_wallet: Optional[str] = Field(
        default=None,
        description="Bitcoin address. Adds the bitcoin dimension (one native BTC presence check).",
    )
    tron_wallet: Optional[str] = Field(
        default=None,
        description="Tron wallet address (T-prefixed). Adds the tron dimension (USDT, USD1, WBTC on Tron).",
    )
    stellar_wallet: Optional[str] = Field(
        default=None,
        description="Stellar wallet address (G-prefixed). Adds no dimension; lets the institutional USDC and BENJI on Stellar rows evaluate (classic trustlines).",
    )
    sui_wallet: Optional[str] = Field(
        default=None,
        description="Sui wallet address (0x + 64 hex). Adds no dimension; lets the institutional USDC on Sui and tokenized-treasury USDY on Sui rows evaluate.",
    )
    proof: Optional[str] = Field(
        default=None,
        description=(
            'Set to "merkle" to include EIP-1186 Merkle storage proofs. '
            "Costs 6 credits instead of 3. Proofs cover EVM token checks on "
            "27 of the 31 EVM chains (not ZKsync Era, Sei, Viction or XDC "
            "Network); rows whose balance is computed rather than stored "
            "(Aave aTokens, BUIDL), NFT rows, non-EVM rows and account rows "
            "(proof.available false, with a reason pointing at /v1/attest) are "
            "declined with a reason, and the premium is refunded whenever no "
            "proof is delivered."
        ),
    )


class InsumerWalletTrustTool(BaseTool):
    """Generate a structured, ECDSA-signed wallet trust fact profile.

    Checks 155 curated conditions across 27 chains in 10 dimensions: stablecoins
    (USDC, USDT, OUSD, PYUSD, USDG, USD1, RLUSD, USDS, DAI, EURC; 52 checks on
    23 EVM chains), governance tokens (8), NFTs (3), staking positions (5),
    institutional stablecoins (8, across Ethereum, Solana, XRPL, Stellar and
    Sui), tokenized treasuries (16: BUIDL, USYC, OUSG, USTB, USDY), stablecoin
    deposits (39: Aave v3 aUSDC/aUSDT, sUSDS, sDAI, listed Morpho USDC vaults),
    wrapped bitcoin (12: cbBTC, WBTC, tBTC), names (2: ENS .eth, Basenames) and
    account (10: contract code or EIP-7702 delegation present at the wallet
    address on Ethereum, Base, Arbitrum, Optimism and Polygon; two rows per
    chain, exclusive, a plain key reads false on both; which contract is never
    named). Up to 176 checks across 29 chains in 14 dimensions with the
    optional Solana, XRPL, Bitcoin and Tron wallets; Stellar and Sui wallets
    add no dimension but let their rows inside the base dimensions evaluate.
    Every check is a presence check. Checks whose chain wallet was not supplied
    carry evaluated: false and are counted in notEvaluatedCount, never as
    passed or failed. The signed conditionSetVersion (currently "2026-10-08")
    names the check list that was run; log it, never reject on it. Dimensions
    come back in a fixed order: the base dimensions in the order above, then
    whichever of solana, xrpl, bitcoin and tron were switched on, in that order.
    Returns per-dimension pass/fail counts and overall summary. No score, no
    opinion, just cryptographically verifiable evidence. Costs 3 credits
    (standard) or 6 credits (with proof="merkle").
    """

    name: str = "insumer_wallet_trust"
    description: str = (
        "Generate a wallet trust fact profile. 155 base checks across 27 chains "
        "in 10 dimensions: stablecoins (USDC, USDT, OUSD, PYUSD, USDG, USD1, "
        "RLUSD, USDS, DAI, EURC), governance tokens (UNI, AAVE, ARB, OP, ENS, "
        "LDO, SKY, COMP), NFTs (BAYC, Pudgy Penguins, Wrapped CryptoPunks), "
        "staking positions (stETH, rETH, cbETH, wstETH, weETH), institutional "
        "stablecoins, tokenized treasuries (BUIDL, USYC, OUSG, USTB, USDY), "
        "stablecoin deposits (Aave v3, sUSDS, sDAI, Morpho USDC vaults), wrapped "
        "bitcoin (cbBTC, WBTC, tBTC), names (ENS, Basenames) and account "
        "(contract code or EIP-7702 delegation present at the wallet address on "
        "Ethereum, Base, Arbitrum, Optimism and Polygon; a plain key reads false "
        "on both rows of a chain). Up to 176 "
        "checks across 29 chains in 14 dimensions with optional Solana, XRPL, "
        "Bitcoin and Tron wallets; Stellar and Sui wallets switch on rows inside "
        "the base dimensions. Every check is a presence check; a check whose "
        "chain wallet was not supplied is reported as evaluated: false, not as "
        'a failure. The signed conditionSetVersion (currently "2026-10-08") '
        "names the check list run; dimensions come back in a fixed order. "
        "Returns per-dimension pass/fail counts and ECDSA-signed "
        "evidence, no score, just facts. Use this when you need a comprehensive wallet "
        'assessment without specifying individual conditions. Costs 3 credits '
        '(standard) or 6 credits (proof="merkle").'
    )
    args_schema: Type[WalletTrustSchema] = WalletTrustSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        wallet: str,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        proof: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Generate the wallet trust fact profile."""
        result = self.api_wrapper.wallet_trust(
            wallet=wallet,
            solana_wallet=solana_wallet,
            xrpl_wallet=xrpl_wallet,
            bitcoin_wallet=bitcoin_wallet,
            tron_wallet=tron_wallet,
            stellar_wallet=stellar_wallet,
            sui_wallet=sui_wallet,
            proof=proof,
        )
        return json.dumps(result, indent=2)
