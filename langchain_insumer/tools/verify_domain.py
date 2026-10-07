"""Tool for verifying domain ownership."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class VerifyDomainSchema(BaseModel):
    """Input for InsumerVerifyDomainTool."""

    merchant_id: str = Field(description="Merchant ID.")


class InsumerVerifyDomainTool(BaseTool):
    """Verify domain ownership for a merchant.

    Call after placing the verification token (from
    ``insumer_request_domain_verification``) via DNS TXT record, HTML meta
    tag, or file upload. The server checks all three methods automatically.
    Rate limited per merchant (a 429 says when to retry). Owner only.
    """

    name: str = "insumer_verify_domain"
    description: str = (
        "Verify domain ownership for a merchant. Call after placing the "
        "verification token via DNS TXT, meta tag, or file. The server "
        "checks all three methods automatically. Rate limited per merchant "
        "(a 429 says when to retry). Owner only."
    )
    args_schema: Type[VerifyDomainSchema] = VerifyDomainSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        merchant_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Verify domain ownership."""
        result = self.api_wrapper.verify_domain(merchant_id=merchant_id)
        return json.dumps(result, indent=2)
