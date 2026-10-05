"""Tool for ACP (Agentic Commerce Protocol) format discount eligibility checks."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class AcpDiscountSchema(BaseModel):
    """Input for InsumerAcpDiscountTool."""

    merchant_id: str = Field(description="Merchant identifier.")
    wallet: Optional[str] = Field(
        default=None,
        description="EVM wallet address (0x...).",
    )
    solana_wallet: Optional[str] = Field(
        default=None,
        description="Solana wallet address (base58).",
    )
    xrpl_wallet: Optional[str] = Field(
        default=None,
        description="XRPL wallet address (r-address).",
    )
    items: Optional[list] = Field(
        default=None,
        description=(
            "Optional line items for per-item cent-amount allocations. "
            "Each dict has 'path' (JSONPath, e.g. '$.line_items[0]') and 'amount' (cents)."
        ),
    )


class InsumerAcpDiscountTool(BaseTool):
    """Check discount eligibility in ACP (OpenAI/Stripe Agentic Commerce Protocol) format.

    Returns coupon objects, applied/rejected arrays, and per-item allocations
    compatible with ACP checkout flows. Same on-chain verification as
    insumer_verify, wrapped in ACP format. Costs 1 merchant credit.
    """

    name: str = "insumer_acp_discount"
    description: str = (
        "Check token-holder discount eligibility in OpenAI/Stripe Agentic Commerce "
        "Protocol (ACP) format. Returns coupon objects, applied/rejected arrays, and "
        "per-item allocations. Same verification as insumer_verify, in ACP format. "
        "Costs 1 merchant credit."
    )
    args_schema: Type[AcpDiscountSchema] = AcpDiscountSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        items: Optional[list] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Check ACP discount eligibility."""
        result = self.api_wrapper.acp_discount(
            merchant_id=merchant_id,
            wallet=wallet,
            solana_wallet=solana_wallet,
            xrpl_wallet=xrpl_wallet,
            items=items,
        )
        return json.dumps(result, indent=2)
