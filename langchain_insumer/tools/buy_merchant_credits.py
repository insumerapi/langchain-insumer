"""Tool for adding credits to the API key that owns a store, with USDC, USDT, or BTC."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyMerchantCreditsSchema(BaseModel):
    """Input for InsumerBuyMerchantCreditsTool."""

    id: str = Field(description="ID of the merchant whose owner key receives the credits.")
    tx_hash: str = Field(description="Transaction hash of the USDC, USDT, BTC, or USDT-TRC20 payment to the platform wallet.")
    chain_id: Any = Field(
        description=(
            "Chain where payment was sent: 1 (Ethereum), 8453 (Base), "
            '137 (Polygon), 42161 (Arbitrum), 10 (Optimism), 56 (BNB), '
            '43114 (Avalanche), "solana", "bitcoin", or "tron" (USDT-TRC20).'
        ),
    )
    amount: Optional[float] = Field(
        default=None,
        description="Stablecoin amount sent (min 5). Not required for BTC: USD value derived from on-chain BTC amount at market rate.",
    )
    update_wallet: bool = Field(
        default=False,
        description="Set true to update the registered sender wallet to this transaction's sender.",
    )


class InsumerBuyMerchantCreditsTool(BaseTool):
    """Add credits to the API key that owns a store, with USDC, USDT, or BTC. Owner only.

    Flat 25 credits per $1 ($0.04/credit). Minimum 5. The credits land on
    the API key that owns the store; a store has no balance of its own.
    """

    name: str = "insumer_buy_merchant_credits"
    description: str = (
        "Add credits to the API key that owns a store by submitting a "
        "USDC, USDT, or BTC transaction hash. Flat 25 credits per $1. "
        "Minimum 5. Owner only. The credits land on the API key that owns "
        "the store; a store has no balance of its own."
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
        amount: Optional[float] = None,
        update_wallet: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Add credits to the store owner's API key."""
        result = self.api_wrapper.buy_merchant_credits(
            merchant_id=id,
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            update_wallet=update_wallet,
        )
        return json.dumps(result, indent=2)
