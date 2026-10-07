"""Tool for listing registered tokens and NFT collections."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class ListTokensSchema(BaseModel):
    """Input for InsumerListTokensTool."""

    chain: Optional[Any] = Field(
        default=None,
        description='Filter by chain ID (e.g. 1 for Ethereum, "solana" for Solana).',
    )
    symbol: Optional[str] = Field(
        default=None,
        description="Filter by token symbol (e.g. UNI).",
    )
    asset_type: Optional[str] = Field(
        default=None,
        description='Filter by type: "token" or "nft".',
    )


class InsumerListTokensTool(BaseTool):
    """List tokens and NFT collections registered with merchants."""

    name: str = "insumer_list_tokens"
    description: str = (
        "List the tokens and NFT collections listed in the Insumer registry. "
        "Filter by blockchain, symbol, or asset type (token/nft). Returns "
        "contract addresses, chain IDs, and metadata. The registry is a "
        "directory, not the list of what can be checked: an attestation can "
        "check any token on a supported chain, and NFTs on EVM chains, Solana "
        "and XRPL, whether listed or not. An empty result means nothing is "
        "listed under that filter, not that the token is unsupported."
    )
    args_schema: Type[ListTokensSchema] = ListTokensSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        chain: Optional[Any] = None,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """List tokens."""
        result = self.api_wrapper.list_tokens(
            chain=chain,
            symbol=symbol,
            asset_type=asset_type,
        )
        return json.dumps(result, indent=2)
