"""Tool for creating a new merchant."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class CreateMerchantSchema(BaseModel):
    """Input for InsumerCreateMerchantTool."""

    company_name: str = Field(
        description="Company display name (max 100 characters).",
        max_length=100,
    )
    company_id: str = Field(
        description=(
            "Unique merchant ID (2-50 chars, alphanumeric, dashes, underscores)."
        ),
        min_length=2,
        max_length=50,
    )
    location: Optional[str] = Field(
        default=None,
        description="City or region (max 200 characters).",
        max_length=200,
    )


class InsumerCreateMerchantTool(BaseTool):
    """Create a new merchant on InsumerAPI.

    A merchant has no balance of its own: codes draw on the credits of the API key that owns it. Maximum 10
    merchants per API key. After creation, use ``insumer_configure_tokens``,
    ``insumer_configure_nfts``, and ``insumer_publish_directory`` to complete
    the onboarding flow.
    """

    name: str = "insumer_create_merchant"
    description: str = (
        "Create a new merchant on InsumerAPI. Provide a company name and "
        "unique ID. Discount codes draw on the credits of the API key that owns the merchant. "
        "Max 10 merchants per API key. After creation, configure tokens "
        "and NFTs, then publish to the directory."
    )
    args_schema: Type[CreateMerchantSchema] = CreateMerchantSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        company_name: str,
        company_id: str,
        location: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Create merchant."""
        result = self.api_wrapper.create_merchant(
            company_name=company_name,
            company_id=company_id,
            location=location,
        )
        return json.dumps(result, indent=2)
