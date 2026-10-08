"""Tool for creating privacy-preserving on-chain verifications."""

import json
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_insumer.wrapper import InsumerAPIWrapper


class AttestSchema(BaseModel):
    """Input for InsumerAttestTool."""

    wallet: Optional[str] = Field(
        default=None,
        description="EVM wallet address (0x...) to verify.",
    )
    solana_wallet: Optional[str] = Field(
        default=None,
        description="Solana wallet address (base58) to verify.",
    )
    xrpl_wallet: Optional[str] = Field(
        default=None,
        description="XRPL wallet address (r-address). For verifying XRP, trust line tokens (RLUSD, USDC), or NFTs on XRP Ledger.",
    )
    bitcoin_wallet: Optional[str] = Field(
        default=None,
        description='Bitcoin address (P2PKH, P2SH, bech32, or Taproot). For verifying native BTC. Use chainId "bitcoin" with contractAddress "native".',
    )
    tron_wallet: Optional[str] = Field(
        default=None,
        description='Tron wallet address (T-prefixed). For verifying TRX or TRC20 tokens (USDT-TRC20). Use chainId "tron".',
    )
    stellar_wallet: Optional[str] = Field(
        default=None,
        description='Stellar wallet address (G-prefixed). For verifying XLM or classic trustline assets (USDC, BENJI, etc.). Use chainId "stellar"; pass assetCode on the condition.',
    )
    sui_wallet: Optional[str] = Field(
        default=None,
        description='Sui wallet address (0x + 64 hex). For verifying SUI or Sui-native tokens (USDC). Use chainId "sui" with the full coin type (address::module::Name) as contractAddress. Native SUI is "0x2::sui::SUI"; "native" is not accepted on Sui.',
    )
    proof: Optional[str] = Field(
        default=None,
        description=(
            'Set to "merkle" to include EIP-1186 Merkle proofs in results: a storage proof '
            "of the balance slot for token_balance and ratio_to_amount conditions (an account proof, "
            "subject account_balance, when contractAddress is native), an account proof (subject account_code) for "
            "account_code conditions, and a revocation-slot proof (subject delegation_revocation) for "
            "erc7710_delegation conditions, on 27 of the 31 EVM chains "
            "(not ZKsync Era, Sei, Viction or XDC Network). "
            "Costs 2 credits instead of 1 (refunded to 1 when no proof is delivered). "
            "A storage proof reveals the raw balance to the caller; an account proof carries codeHash, never the code."
        ),
    )
    format: Optional[str] = Field(
        default=None,
        description=(
            'Set to "jwt" to include a Wallet Auth by InsumerAPI token (ES256-signed JWT) '
            "in the response. Verifiable by any standard JWT library using JWKS at "
            "/.well-known/jwks.json. No additional cost."
        ),
    )
    conditions: str = Field(
        description=(
            'JSON array of conditions. Each condition: {"type": "token_balance" or '
            '"nft_ownership" or "eas_attestation" or "farcaster_id" or "evm_view_call" or "ratio_to_amount" or '
            '"ratio_to_supply" or "erc8004_agent" or "erc7710_delegation" or "account_code", "contractAddress": "0x...", '
            '"chainId": 1, "threshold": "1000", "label": "USDC >= 1000"}. '
            'threshold is a decimal string in token units (e.g. "1000", not 1000). '
            "decimals is optional. Leave it out: the token's own decimals are always read from the chain. "
            "If sent it is only a cross-check, and a value that differs from the token's own decimals is rejected with a 400. "
            'contractAddress "native" is for token_balance and ratio_to_amount only; nft_ownership needs the NFT contract address (0x + 40 hex on EVM) and "native" there is a 400. '
            'On Sui, contractAddress is the full coin type (native SUI is "0x2::sui::SUI"; "native" is not accepted on Sui). '
            'For eas_attestation: use "template": "coinbase_verified_account" (or '
            '"coinbase_verified_country", "coinbase_one", "gitcoin_passport_score", '
            '"gitcoin_passport_active") instead of contractAddress, '
            'or specify raw "schemaId", "attester", "indexer", "chainId". '
            'For farcaster_id: no extra fields needed (checks IdRegistry on Optimism). '
            'For ratio_to_amount (EVM chains only): add "multiple" and "amount" as decimal strings (e.g. "10", "100") (met iff balance >= multiple * amount). '
            'For ratio_to_supply (EVM chains only, ERC-20 only): add "minFraction" as a decimal string in (0,1] (e.g. "0.005") (met iff balance / totalSupply >= minFraction). '
            'For evm_view_call (EVM chains only): add "selector" as the canonical signature of a single-address-argument view function returning bool (e.g. "hasAccess(address)"). '
            'For erc8004_agent (Base, chainId 8453): add "agentId" as a uint256 decimal string (met iff the wallet owns the agent NFT or is the registry agentWallet binding; registration is permissionless, no vetting implied). '
            'For erc7710_delegation (Base, chainId 8453, max 3 per call): add "delegationManager" (a recognized MetaMask Delegation Framework manager), "expectedDelegator" (the asserted principal), and "delegation" ({delegator, delegate, authority, caveats, salt, signature}); met iff the wallet is the delegate, the delegator matches, the EIP-712 signature verifies (EOA or ERC-1271), unrevoked at the anchored block, all caveat enforcers recognized, time windows satisfied. Spend/target/call limits are reported as declaredLimits, not simulated. Delegation attestations expire in 5 minutes. '
            'For account_code (EVM chains only; no contractAddress): add "expect", one of "none" (no code: a plain key account), "eip7702" (the EIP-7702 delegation designator: a key that has delegated execution to a contract) or "contract" (any other code: a smart-contract wallet, a protocol, a token); met iff the wallet address itself is in that code state at the anchored block (the three states are exclusive on a chain). Optional "delegate" (an EVM address, only with expect "eip7702"; a 400 with any other expect): met iff the designator points at it. The answer is met only: the code and the delegation target are never returned, in any format or mode; a supplied delegate is echoed inside the signed evaluatedCondition. With proof="merkle" the proof is an EIP-1186 account proof with subject "account_code" (blockNumber, nonce, balance, storageHash, codeHash, accountProof). Example: {"type": "account_code", "chainId": 8453, "expect": "eip7702"}. '
            'currency: XRPL trust line currency code (e.g. "RLUSD"); required for XRPL trust line tokens (contractAddress is the issuer r-address). Codes are case-sensitive: send the code exactly as the issuer created it and never change its letter case. To check XRP itself use contractAddress "native" with no currency; "XRP" is not a trust line currency. '
            "taxon: XRPL NFToken taxon filter (optional): a whole number from 0 to 4294967295. "
            'assetCode: Stellar trustline asset code (e.g. "USDC", "BENJI"); required for Stellar non-native tokens. '
            "Supported chains: Ethereum (1), XDC (50), BNB (56), Base (8453), Polygon (137), "
            "Arbitrum (42161), Optimism (10), Avalanche (43114), World Chain (480), "
            'Solana ("solana"), XRPL ("xrpl"), Bitcoin ("bitcoin"), Tron ("tron"), '
            'Stellar ("stellar"), Sui ("sui"), Robinhood Chain (4663), Arc (5042), and 20 more EVM. 37 chains total (31 EVM). '
            "nft_ownership is supported on 33 of the 37 (EVM + Solana + XRPL); Bitcoin, Tron, Stellar and Sui are token_balance only. Max 10 conditions per call."
        ),
    )


class InsumerAttestTool(BaseTool):
    """Verify on-chain token balances, NFT ownership, EAS attestations, Farcaster
    identity, view calls, ratios, ERC-8004 registration, ERC-7710 delegations, or
    the account code state (plain key, EIP-7702 delegation, contract code).

    Returns only true/false per condition and never exposes actual balances, code
    or delegation targets.
    The response includes an ECDSA P-256 signature (sig, kid) and an
    ML-DSA-65 post-quantum signature (pqSig, pqKid).
    Costs 1 verification credit per call, or 2 credits with proof="merkle".
    For EAS attestations, use a compliance template (Coinbase Verifications,
    Gitcoin Passport) or raw schemaId. For Farcaster, use type "farcaster_id".
    """

    name: str = "insumer_attest"
    description: str = (
        "Verify on-chain conditions (token balances, NFT ownership, EAS attestations, "
        "Farcaster identity, arbitrary boolean view calls, supply/amount ratios, ERC-8004 "
        "agent registration, ERC-7710 delegation validity, account code state: plain key, "
        "EIP-7702 delegation or contract code) across 37 blockchains. Returns a cryptographically signed "
        "true/false verification without exposing actual wallet balances, code or delegation targets. Use this when "
        "you need to check if a wallet holds a specific token or NFT, has an EAS "
        "attestation (Coinbase Verifications, Gitcoin Passport), is registered on "
        "Farcaster, or is a plain key, an EIP-7702-delegated key or a contract on an EVM chain "
        '(type "account_code" with "expect"). Costs 1 verification credit. '
        'Pass proof="merkle" for EIP-1186 Merkle proofs (2 credits). '
        "Use insumer_compliance_templates to list available EAS templates."
    )
    args_schema: Type[AttestSchema] = AttestSchema

    api_wrapper: InsumerAPIWrapper = Field(..., exclude=True)

    def __init__(self, api_wrapper: InsumerAPIWrapper) -> None:
        super().__init__(api_wrapper=api_wrapper)

    def _run(
        self,
        conditions: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        proof: Optional[str] = None,
        format: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the on-chain verification."""
        parsed_conditions: list[dict[str, Any]] = json.loads(conditions)
        result = self.api_wrapper.attest(
            conditions=parsed_conditions,
            wallet=wallet,
            solana_wallet=solana_wallet,
            xrpl_wallet=xrpl_wallet,
            bitcoin_wallet=bitcoin_wallet,
            tron_wallet=tron_wallet,
            stellar_wallet=stellar_wallet,
            sui_wallet=sui_wallet,
            proof=proof,
            format=format,
        )
        return json.dumps(result, indent=2)
