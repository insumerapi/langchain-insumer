"""Tool for buying a new API key with USDC (no auth required)."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyKeySchema(BaseModel):
    """Input for InsumerBuyKeyTool."""

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
    app_name: str = Field(
        description="Name for the API key (e.g. your agent or app name). Max 100 chars.",
        max_length=100,
    )
    sender_signature: Optional[str] = Field(
        default=None,
        description=(
            "Signature by the wallet that sent the payment over the exact text "
            "the API names for this payment. Required for every key purchase. "
            "Call without it once to receive the text to sign in the 400 error. "
            "EVM: EIP-191 personal_sign, 0x hex (smart wallets via ERC-1271). "
            "Solana: ed25519 signMessage, base58 or base64."
        ),
    )


class InsumerBuyKeyTool(BaseTool):
    """Buy a new API key with USDC. No auth required.

    Agent-friendly: no email needed. Send USDC to the platform wallet,
    sign the text the API names for that payment with the sending wallet,
    then call this tool with the transaction hash and the signature. The
    sender wallet becomes the key's identity. One key per wallet.
    """

    name: str = "insumer_buy_key"
    description: str = (
        "Buy a new API key with USDC (no auth required). "
        "Agent-friendly: no email needed, the sender wallet becomes the "
        "key's identity. One key per wallet. Volume discounts: "
        "$0.04-$0.02/call. USDC on 7 EVM chains or Solana. The wallet that "
        "paid signs the text the API returns for the payment (sender_signature). "
        "Non-refundable."
    )
    args_schema: Type[BuyKeySchema] = BuyKeySchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        tx_hash: str,
        chain_id: Any,
        amount: float,
        app_name: str,
        sender_signature: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Buy a new API key."""
        result = self.api_wrapper.buy_key(
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            app_name=app_name,
            sender_signature=sender_signature,
        )
        return json.dumps(result, indent=2)
