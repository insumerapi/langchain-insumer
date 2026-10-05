"""Tool for creating signed discount verification codes."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class VerifySchema(BaseModel):
    """Input for InsumerVerifyTool."""

    merchant_id: str = Field(description="Merchant ID to generate the discount code for.")
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


class InsumerVerifyTool(BaseTool):
    """Create a signed discount verification code for a wallet at a merchant.

    Returns tier and discount percentage -- never raw balance amounts.
    The code (INSR-XXXXX) is valid for 30 minutes and can be redeemed
    at the merchant's point of sale. Costs 1 merchant credit.
    """

    name: str = "insumer_verify"
    description: str = (
        "Create a signed discount verification code (INSR-XXXXX) for a wallet "
        "at a specific merchant. Returns tier and discount percentage -- never "
        "raw balance amounts. The code is valid for 30 minutes and includes "
        "an ECDSA signature. Costs 1 merchant credit."
    )
    args_schema: Type[VerifySchema] = VerifySchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Create verification code."""
        result = self.api_wrapper.verify(
            merchant_id=merchant_id,
            wallet=wallet,
            solana_wallet=solana_wallet,
            xrpl_wallet=xrpl_wallet,
        )
        return json.dumps(result, indent=2)
