"""Tool for updating merchant settings."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class ConfigureSettingsSchema(BaseModel):
    """Input for InsumerConfigureSettingsTool."""

    id: str = Field(description="Merchant ID to configure settings for.")
    discount_mode: Optional[str] = Field(
        default=None,
        description=(
            'Discount stacking mode: "highest" (best single discount wins) '
            'or "stack" (discounts add up to discount_cap).'
        ),
    )
    discount_cap: Optional[int] = Field(
        default=None,
        description="Maximum total discount percentage: a whole number from 1 to 100 (no decimals).",
        ge=1,
        le=100,
    )
    usdc_payment: Optional[str] = Field(
        default=None,
        description=(
            "JSON object for USDC payment settings, or null to disable. "
            '{"enabled": true, "evmAddress": "0x...", "solanaAddress": "...", '
            '"preferredChainId": 8453}. Pass as a JSON string.'
        ),
    )


class InsumerConfigureSettingsTool(BaseTool):
    """Update merchant settings: discount mode, cap, and USDC payments. Owner only.

    All fields are optional — only provided fields are updated.
    """

    name: str = "insumer_configure_settings"
    description: str = (
        "Update merchant settings. Options: discount stacking mode "
        '("highest" or "stack"), discount cap (a whole number from 1 to 100), and USDC payment '
        "configuration (wallet addresses, preferred chain). All fields "
        "optional. Owner only."
    )
    args_schema: Type[ConfigureSettingsSchema] = ConfigureSettingsSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        id: str,
        discount_mode: Optional[str] = None,
        discount_cap: Optional[int] = None,
        usdc_payment: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Configure settings."""
        parsed_usdc: Optional[dict] = None
        if usdc_payment is not None:
            parsed_usdc = json.loads(usdc_payment)
        result = self.api_wrapper.configure_settings(
            merchant_id=id,
            discount_mode=discount_mode,
            discount_cap=discount_cap,
            usdc_payment=parsed_usdc,
        )
        return json.dumps(result, indent=2)
