"""Tool for buying a new API key with USDC, USDT, or BTC (no auth required)."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class BuyKeySchema(BaseModel):
    """Input for InsumerBuyKeyTool."""

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
        ge=5,
    )
    app_name: str = Field(
        description="Name for the API key (e.g. your agent or app name). Max 100 chars.",
        max_length=100,
    )


class InsumerBuyKeyTool(BaseTool):
    """Buy a new API key with USDC, USDT, or BTC. No auth required.

    Agent-friendly: no email needed. Send USDC, USDT, or BTC to the
    platform wallet, then call this tool with the transaction hash.
    The sender wallet becomes the key's identity. One key per wallet.
    """

    name: str = "insumer_buy_key"
    description: str = (
        "Buy a new API key with USDC, USDT, or BTC (no auth required). "
        "Agent-friendly: no email needed, the sender wallet becomes the "
        "key's identity. One key per wallet. Volume discounts: "
        "$0.04-$0.02/call. Supports 7 EVM chains, Solana, Bitcoin and Tron. "
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
        app_name: str,
        amount: Optional[float] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Buy a new API key."""
        result = self.api_wrapper.buy_key(
            tx_hash=tx_hash,
            chain_id=chain_id,
            amount=amount,
            app_name=app_name,
        )
        return json.dumps(result, indent=2)
