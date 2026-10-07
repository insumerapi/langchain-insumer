"""Tool for generating batch wallet trust fact profiles."""

import json
from typing import Any, Literal, Optional, Tuple, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.tools._batch_summary import summarize_batch_trust
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
            'Set to "merkle" to include EIP-1186 Merkle storage proofs on EVM '
            "token checks. Account rows carry proof.available false with a "
            "reason pointing at /v1/attest. Costs 6 credits per wallet instead of 3."
        ),
    )
    detail: Literal["summary", "full"] = Field(
        default="summary",
        description=(
            '"summary" (default): the text is a short summary per wallet and the '
            "complete signed profiles are in the tool result's artifact. "
            '"full": the complete signed profiles as text too, tens of thousands '
            "of characters per wallet. Choose it on the call that needs it: "
            "profiles cannot be fetched again, so a second call signs fresh "
            "profiles and is charged again. Not sent to the API."
        ),
    )


class InsumerBatchWalletTrustTool(BaseTool):
    """Generate wallet trust fact profiles for up to 10 wallets in one request.

    Shared block fetches make this 5-8x faster than sequential calls. Each
    wallet gets an independently ECDSA-signed profile with the same
    dimensions as the single-wallet tool (155 base checks across 27 chains in
    10 dimensions, up to 176 across 29 chains in 14 with the optional Solana,
    XRPL, Bitcoin and Tron wallets; the account dimension reports contract
    code or EIP-7702 delegation present on Ethereum, Base, Arbitrum, Optimism
    and Polygon), in the same fixed dimension order for every wallet; the
    signed conditionSetVersion (currently "2026-10-08") names the check list
    run. Supports partial success. Costs 3 credits per successful wallet
    (standard) or 6 credits per wallet (with proof="merkle"). Credits only
    charged for successes.

    The tool returns content and an artifact. The content, which is what a
    model reads, is a per-wallet summary by default; the artifact is the
    complete API response with every signed profile, unchanged.
    """

    name: str = "insumer_batch_wallet_trust"
    description: str = (
        "Generate wallet trust fact profiles for up to 10 wallets in a single "
        "request. Shared block fetches make this 5-8x faster than sequential "
        "calls. Each wallet gets an independently ECDSA-signed profile with "
        "its own TRST-XXXXX ID: 155 base checks across 27 chains in 10 "
        "dimensions (stablecoins, governance, nfts, staking, "
        "institutional_stablecoins, tokenized_treasuries, stablecoin_deposits, "
        "wrapped_bitcoin, names, account), up to 176 across 29 chains in 14 "
        "with the optional wallets, in a fixed dimension order for every "
        "wallet. Supports partial success. Costs 3 credits per "
        'successful wallet (standard) or 6 per wallet (proof="merkle"). '
        "Each profile lists every check, so the response is large; by default "
        "the text is a summary per wallet (profile ID, held / not held / not "
        "evaluated counts, and the checks held in each dimension; the account "
        "dimension says present) and the "
        "complete signed profiles are returned unchanged as the tool result's "
        'artifact. Set detail="full" on the call to get them as text too.'
    )
    args_schema: Type[BatchWalletTrustSchema] = BatchWalletTrustSchema
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        wallets: list[dict],
        proof: Optional[str] = None,
        detail: str = "summary",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, Any]:
        """Generate batch wallet trust fact profiles."""
        result = self.api_wrapper.batch_wallet_trust(
            wallets=wallets,
            proof=proof,
        )
        summary = None if detail == "full" else summarize_batch_trust(result)
        if summary is None:
            return json.dumps(result, indent=2), result
        return summary, result
