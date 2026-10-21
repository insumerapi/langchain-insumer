"""Tool for adding credits to the API key that owns a store, with USDC."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyMerchantCreditsSchema(BaseModel):
    """Input for InsumerBuyMerchantCreditsTool."""

    id: str = Field(description="ID of the merchant whose owner key receives the credits.")
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
            "the API names for this payment. Required when the owner key has "
            "no registered wallet yet, or with update_wallet for a different "
            "sender; not needed when the registered wallet paid. Call without "
            "it once to receive the text to sign in the 400 error. EVM: "
            "EIP-191 personal_sign, 0x hex (smart wallets via ERC-1271). "
            "Solana: ed25519 signMessage, base58 or base64."
        ),
    )


class InsumerBuyMerchantCreditsTool(BaseTool):
    """Add credits to the API key that owns a store, with USDC. Owner only.

    Flat 25 credits per $1 ($0.04/credit). Minimum 5. The credits land on
    the API key that owns the store; a store has no balance of its own.
    """

    name: str = "insumer_buy_merchant_credits"
    description: str = (
        "Add credits to the API key that owns a store by submitting a "
        "USDC transaction hash. Flat 25 credits per $1. "
        "Minimum 5. Owner only. USDC on 7 EVM chains or Solana. The credits "
        "land on the API key that owns the store; a store has no balance of "
        "its own. A key with no registered wallet, or a wallet change, takes "
        "the paying wallet's signature (sender_signature)."
    )
    args_schema: Type[BuyMerchantCreditsSchema] = BuyMerchantCreditsSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        id: str,
        tx_hash: str,
        chain_id: Any,
        amount: float,
        update_wallet: bool = False,
        sender_signature: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Add credits to the store owner's API key."""
        result = self.api_wrapper.buy_merchant_credits(
            merchant_id=id,
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            update_wallet=update_wallet,
            sender_signature=sender_signature,
        )
        return json.dumps(result, indent=2)
