"""Tool for configuring merchant NFT collection discounts."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class ConfigureNftsSchema(BaseModel):
    """Input for InsumerConfigureNftsTool."""

    id: str = Field(description="Merchant ID to configure NFTs for.")
    nft_collections: str = Field(
        description=(
            "JSON array of NFT collection configurations (0-4). Each: "
            '{"name": "Collection Name", "contractAddress": "0x...", '
            '"chainId": 1, "discount": 10}. Discount is a whole number from 1 to 50 '
            "(no decimals; 7.5 is refused with a 400). "
            'For an XRPL collection (chainId "xrpl") contractAddress is the issuer '
            'r-address, and an optional "taxon" (a whole number from 0 to 4294967295) '
            "limits it to one taxon. "
            '"enabled" is optional; if sent it must be JSON true or false, never a string. '
            "The array replaces the stored list. "
            "Pass as a JSON string."
        ),
    )


class InsumerConfigureNftsTool(BaseTool):
    """Configure NFT collections that grant discounts at a merchant. Owner only.

    Max 4 NFT collections per merchant. Each collection specifies a
    contract address, chain, and flat discount percentage (a whole number
    from 1 to 50).
    """

    name: str = "insumer_configure_nfts"
    description: str = (
        "Configure NFT collections that grant discounts at a merchant. "
        "Max 4 collections. Each specifies contract address, chain, and "
        "discount percentage (a whole number from 1 to 50). XRPL collections "
        "take the issuer r-address and an optional taxon. enabled, if sent, "
        "must be true or false. Owner only. Pass nft_collections "
        "as a JSON array string."
    )
    args_schema: Type[ConfigureNftsSchema] = ConfigureNftsSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        id: str,
        nft_collections: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Configure NFTs."""
        parsed: list = json.loads(nft_collections)
        result = self.api_wrapper.configure_nfts(
            merchant_id=id,
            nft_collections=parsed,
        )
        return json.dumps(result, indent=2)
