"""Tool for fetching the InsumerAPI JWKS (public signing keys)."""

import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class JwksSchema(BaseModel):
    """Input for InsumerJwksTool (no parameters required)."""

    pass


class InsumerJwksTool(BaseTool):
    """Fetch the JWKS containing InsumerAPI's public signing keys.

    Five entries over two keys: the ECDSA P-256 key under three kids
    (insumer-attest-v1, insumer-attest-v2, insumer-trust-v2) followed by the
    ML-DSA-65 post-quantum key under two RFC 9964 AKP entries
    (insumer-attest-pq1, insumer-trust-pq1). The kid and pqKid fields in
    attestation and trust responses identify which entries signed the
    response; match on them, never on position. No authentication required.
    """

    name: str = "insumer_jwks"
    description: str = (
        "Get the JWKS (JSON Web Key Set) containing InsumerAPI's public signing "
        "keys: the ECDSA P-256 key under three kids and the ML-DSA-65 "
        "post-quantum key under two RFC 9964 AKP entries. Match the "
        "kid and pqKid fields from attestation responses to the correct entry, "
        "never by position. Enables signature verification and automatic key "
        "rotation. Free, no credits consumed."
    )
    args_schema: Type[JwksSchema] = JwksSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Fetch the JWKS document."""
        result = self.api_wrapper.get_jwks()
        return json.dumps(result, indent=2)
