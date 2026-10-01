"""Tool for generating batch wallet trust fact profiles."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BatchWalletTrustSchema(BaseModel):
    """Input for InsumerBatchWalletTrustTool."""

    wallets: list[dict] = Field(
        description=(
            "List of 1-10 wallet objects. Each must have 'wallet' (EVM address). "
            "Optional 'solanaWallet' (base58) adds the 14-check solana dimension and lets the institutional EURCV/USDCV on Solana rows evaluate. "
            "Optional 'xrplWallet' (r-address) adds the xrpl dimension (RLUSD, USDC, OUSG) and lets the institutional EURCV on XRPL row evaluate. "
            "Optional 'bitcoinWallet' adds the bitcoin dimension (native BTC). "
            "Optional 'tronWallet' (T-prefixed) adds the tron dimension (USDT, USD1, WBTC). "
            "Optional 'stellarWallet' (G-prefixed) adds no dimension; lets the institutional USDC and BENJI on Stellar rows evaluate (classic trustlines). "
            "Optional 'suiWallet' (0x + 64 hex) adds no dimension; lets the institutional USDC on Sui and tokenized-treasury USDY on Sui rows evaluate."
        ),
    )
    proof: Optional[str] = Field(
        default=None,
        description=(
            'Set to "merkle" to include EIP-1186 Merkle storage proofs. '
            "Costs 6 credits per wallet instead of 3."
        ),
    )


class InsumerBatchWalletTrustTool(BaseTool):
    """Generate wallet trust fact profiles for up to 10 wallets in one request.

    Shared block fetches make this 5-8x faster than sequential calls. Each
    wallet gets an independently ECDSA-signed profile. Supports partial
    success. Costs 3 credits per successful wallet (standard) or 6 credits
    per wallet (with proof="merkle"). Credits only charged for successes.
    """

    name: str = "insumer_batch_wallet_trust"
    description: str = (
        "Generate wallet trust fact profiles for up to 10 wallets in a single "
        "request. Shared block fetches make this 5-8x faster than sequential "
        "calls. Each wallet gets an independently ECDSA-signed profile with "
        "its own TRST-XXXXX ID. Supports partial success. Costs 3 credits per "
        'successful wallet (standard) or 6 per wallet (proof="merkle").'
    )
    args_schema: Type[BatchWalletTrustSchema] = BatchWalletTrustSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        wallets: list[dict],
        proof: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Generate batch wallet trust fact profiles."""
        result = self.api_wrapper.batch_wallet_trust(
            wallets=wallets,
            proof=proof,
        )
        return json.dumps(result, indent=2)
