"""Tool for configuring merchant token discount tiers."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class ConfigureTokensSchema(BaseModel):
    """Input for InsumerConfigureTokensTool."""

    id: str = Field(description="Merchant ID to configure tokens for.")
    own_token: Optional[str] = Field(
        default=None,
        description=(
            "JSON object for the merchant's own token, or null to switch it off. "
            'Format: {"symbol": "TOKEN", "chainId": 1, "contractAddress": "0x...", '
            '"decimals": 18, "tiers": [{"name": "Gold", "threshold": 1000, "discount": 10}]}. '
            "decimals is required. Each tier discount is a whole number from 1 to 50 "
            "(no decimals; 7.5 is refused with a 400). "
            'For an XRPL trust line token (chainId "xrpl", contractAddress is the issuer '
            'r-address) add "currency", e.g. "RLUSD". Currency codes are case-sensitive: '
            "send the code exactly as the issuer created it. "
            '"enabled" is optional; if sent it must be JSON true or false, never a string. '
            "Leave this argument out to keep the stored own token unchanged. "
            "Pass as a JSON string."
        ),
    )
    partner_tokens: Optional[str] = Field(
        default=None,
        description=(
            "JSON array of partner token configurations. Same format and rules as "
            "own_token (whole-number discounts from 1 to 50, XRPL currency exactly as "
            "issued), but as an array. Max 8 tokens total (own + partners). The array "
            "replaces the stored partner list, so include every partner token to keep; "
            "leave this argument out to keep the stored list unchanged. "
            "Pass as a JSON string."
        ),
    )


class InsumerConfigureTokensTool(BaseTool):
    """Configure token discount tiers for a merchant. Owner only.

    Set the merchant's own token and/or partner tokens. Each token defines
    balance threshold tiers with discount percentages. Max 8 tokens total.
    """

    name: str = "insumer_configure_tokens"
    description: str = (
        "Configure token discount tiers for a merchant. Set own token "
        "and/or partner tokens with balance thresholds and discount "
        "percentages. Max 8 tokens total. Owner only. Token configs are "
        "JSON: {symbol, chainId, contractAddress, decimals, tiers: "
        "[{name, threshold, discount}]}. Discounts are whole numbers from 1 to 50. "
        "XRPL trust line tokens also need currency, sent exactly as issued "
        "(case-sensitive). enabled, if sent, must be true or false. A token "
        "argument left out is not changed."
    )
    args_schema: Type[ConfigureTokensSchema] = ConfigureTokensSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        id: str,
        own_token: Optional[str] = None,
        partner_tokens: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Configure tokens."""
        parsed_own: Optional[dict] = None
        parsed_partners: Optional[list] = None
        if own_token is not None:
            parsed_own = json.loads(own_token)
        if partner_tokens is not None:
            parsed_partners = json.loads(partner_tokens)
        result = self.api_wrapper.configure_tokens(
            merchant_id=id,
            own_token=parsed_own,
            partner_tokens=parsed_partners,
        )
        return json.dumps(result, indent=2)
