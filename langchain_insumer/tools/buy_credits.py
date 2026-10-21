"""Tool for buying verification credits with USDC."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyCreditsSchema(BaseModel):
    """Input for InsumerBuyCreditsTool."""

    tx_hash: str = Field(description="Transaction hash of the USDC payment to the platform wallet.")
    chain_id: Any = Field(
        description=(
            "Chain where the USDC payment was sent: 1 (Ethereum), 8453 (Base), "
            '137 (Polygon), 42161 (Arbitrum), 10 (Optimism), 56 (BNB Chain), '
            '43114 (Avalanche), or "solana". Purchases are paid in USDC only.'
        ),
    )
    amount: float = Field(
        description="USDC amount sent (min 5).",
        ge=5,
    )
    update_wallet: bool = Field(
        default=False,
        description=(
            "Set true to update the registered sender wallet to this "
            "transaction's sender. The new wallet signs the payment text "
            "(sender_signature)."
        ),
    )
    sender_signature: Optional[str] = Field(
        default=None,
        description=(
            "Signature by the wallet that sent the payment over the exact text "
            "the API names for this payment. Required when the key has no "
            "registered wallet yet, or with update_wallet for a different "
            "sender; not needed when the registered wallet paid. Call without "
            "it once to receive the text to sign in the 400 error. EVM: "
            "EIP-191 personal_sign, 0x hex (smart wallets via ERC-1271). "
            "Solana: ed25519 signMessage, base58 or base64."
        ),
    )


class InsumerBuyCreditsTool(BaseTool):
    """Buy verification credits with USDC.

    Volume tiers: $5 to $99: 25 credits per $1 ($0.04/credit); $100 to
    $499: 33 per $1 ($0.03); $500 and up: 50 per $1 ($0.02). Minimum
    purchase: 5 (125 credits). The server verifies the on-chain transaction
    receipt.
    """

    name: str = "insumer_buy_credits"
    description: str = (
        "Buy verification credits for the API key by submitting a USDC "
        "transaction hash. 25 to 50 credits per $1 by volume "
        "($0.04 to $0.02/credit). Minimum 5. USDC on 7 EVM chains or "
        "Solana. A key with no registered wallet, or a wallet change, "
        "takes the paying wallet's signature (sender_signature)."
    )
    args_schema: Type[BuyCreditsSchema] = BuyCreditsSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        tx_hash: str,
        chain_id: Any,
        amount: float,
        update_wallet: bool = False,
        sender_signature: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Buy credits."""
        result = self.api_wrapper.buy_credits(
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            update_wallet=update_wallet,
            sender_signature=sender_signature,
        )
        return json.dumps(result, indent=2)
