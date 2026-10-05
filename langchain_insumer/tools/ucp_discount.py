"""Tool for UCP (Universal Commerce Protocol) format discount eligibility checks."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class UcpDiscountSchema(BaseModel):
    """Input for InsumerUcpDiscountTool."""

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


class InsumerUcpDiscountTool(BaseTool):
    """Check discount eligibility in UCP (Google Universal Commerce Protocol) format.

    Returns title, extension field, and applied array compatible with UCP
    checkout flows. Same on-chain verification as insumer_verify, wrapped
    in UCP format. Costs 1 merchant credit.
    """

    name: str = "insumer_ucp_discount"
    description: str = (
        "Check token-holder discount eligibility in Google Universal Commerce "
        "Protocol (UCP) format. Returns title, extension field, and applied array. "
        "Same verification as insumer_verify, in UCP format. "
        "Costs 1 merchant credit."
    )
    args_schema: Type[UcpDiscountSchema] = UcpDiscountSchema

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
        """Check UCP discount eligibility."""
        result = self.api_wrapper.ucp_discount(
            merchant_id=merchant_id,
            wallet=wallet,
            solana_wallet=solana_wallet,
            xrpl_wallet=xrpl_wallet,
            items=items,
        )
        return json.dumps(result, indent=2)
