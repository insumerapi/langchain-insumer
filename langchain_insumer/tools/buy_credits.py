"""Tool for buying verification credits with USDC, USDT, or BTC."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyCreditsSchema(BaseModel):
    """Input for InsumerBuyCreditsTool."""

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


class InsumerBuyCreditsTool(BaseTool):
    """Buy verification credits with USDC, USDT, or BTC.

    Volume tiers: $5 to $99: 25 credits per $1 ($0.04/credit); $100 to
    $499: 33 per $1 ($0.03); $500 and up: 50 per $1 ($0.02). Minimum
    purchase: 5 (125 credits). The server verifies the on-chain transaction
    receipt.
    """

    name: str = "insumer_buy_credits"
    description: str = (
        "Buy verification credits for the API key by submitting a USDC, "
        "USDT, or BTC transaction hash. 25 to 50 credits per $1 by volume "
        "($0.04 to $0.02/credit). Minimum 5. Supports 7 EVM chains, Solana, "
        "Bitcoin and Tron."
    )
    args_schema: Type[BuyCreditsSchema] = BuyCreditsSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        tx_hash: str,
        chain_id: Any,
        amount: Optional[float] = None,
        update_wallet: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Buy credits."""
        result = self.api_wrapper.buy_credits(
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            update_wallet=update_wallet,
        )
        return json.dumps(result, indent=2)
