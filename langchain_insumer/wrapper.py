"""API wrapper for The Insumer Model On-Chain Verification API."""

import os
from typing import Any, Optional

from decimal import Decimal

import requests
from pydantic import BaseModel, Field, model_validator

BASE_URL = "https://api.insumermodel.com/v1"



def _decimal_str(value: Any) -> str:
    """A number as a plain decimal string.

    ``str()`` of a float switches to exponent notation for very small and very
    large values ("1e-07"), which the API does not read as a decimal string.
    """
    if isinstance(value, bool):
        raise ValueError("a condition quantity must be a number or a decimal string, not a bool")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(Decimal(repr(value)), "f")
    return str(value)

def _raise_for_status(resp: requests.Response) -> None:
    """Raise ``requests.HTTPError`` on a 4xx/5xx, carrying the API's own message.

    The API explains a rejected request in its JSON body (``error.message``),
    and a refused read (503) lists the conditions it could not read in
    ``error.failedConditions``. Both are included in the exception message so
    the caller, or the agent, can see what to change. The response is attached
    as ``exc.response``. When the body is not JSON, the plain status error is
    raised.
    """
    status = resp.status_code
    if not isinstance(status, int) or status < 400:
        return
    detail = ""
    try:
        body = resp.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            parts = []
            if err.get("code"):
                parts.append(str(err["code"]))
            if err.get("message"):
                parts.append(str(err["message"]))
            detail = ": ".join(parts)
            failed = err.get("failedConditions")
            if failed:
                detail = f"{detail} (failedConditions: {failed})"
        elif isinstance(err, str):
            detail = err
    if not detail:
        resp.raise_for_status()
        raise requests.HTTPError(f"InsumerAPI returned HTTP {status}", response=resp)
    raise requests.HTTPError(
        f"InsumerAPI returned HTTP {status}: {detail}", response=resp
    )


class InsumerAPIWrapper(BaseModel):
    """Wrapper around The Insumer Model API.

    Provides privacy-preserving on-chain verification and token-gated commerce
    across 37 blockchains (31 EVM + Solana + XRPL + Bitcoin + Tron + Stellar + Sui).
    Verifies token balances and NFT ownership without exposing actual wallet
    balances.

    Args:
        api_key: API key in format ``insr_live_`` followed by 40 hex characters.
            Falls back to the ``INSUMER_API_KEY`` environment variable when
            omitted, so keys stay out of source code.
            Get a free key at https://insumermodel.com/developers/
        timeout: Request timeout in seconds. Default 30.
    """

    api_key: Optional[str] = Field(
        default=None, description="Insumer API key (insr_live_...)"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @model_validator(mode="after")
    def _resolve_api_key(self) -> "InsumerAPIWrapper":
        if not self.api_key:
            self.api_key = os.environ.get("INSUMER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "An API key is required. Pass api_key=... or set the "
                "INSUMER_API_KEY environment variable. "
                "Get a free key at https://insumermodel.com/developers/"
            )
        return self

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = requests.get(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def _public_post(self, path: str, json_body: Optional[dict] = None) -> dict:
        resp = requests.post(
            f"{BASE_URL}{path}",
            headers={"Content-Type": "application/json"},
            json=json_body or {},
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def _post(self, path: str, json_body: Optional[dict] = None) -> dict:
        resp = requests.post(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            json=json_body or {},
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def _put(self, path: str, json_body: Optional[dict] = None) -> dict:
        resp = requests.put(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            json=json_body or {},
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def get_jwks(self) -> dict:
        """Get the JWKS containing InsumerAPI's public signing keys.

        Five entries over two keys: the ECDSA P-256 key under the kids
        ``insumer-attest-v1``, ``insumer-attest-v2`` and ``insumer-trust-v2``,
        followed by the ML-DSA-65 post-quantum companion key under two RFC 9964
        ``AKP`` entries, ``insumer-attest-pq1`` and ``insumer-trust-pq1``.
        No authentication required. Match the ``kid`` (and ``pqKid``) on a
        response to its entry, never by position, enabling automatic key
        rotation.

        Returns:
            JWKS document with the public signing keys.
        """
        resp = requests.get(
            f"{BASE_URL}/jwks",
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def get_compliance_templates(self) -> dict:
        """List available compliance templates for EAS attestation verification.

        Returns pre-configured templates for KYC/identity providers (e.g.
        Coinbase Verifications on Base). No authentication required.

        Returns:
            Template catalog with provider, description, chainId, and chainName.
        """
        resp = requests.get(
            f"{BASE_URL}/compliance/templates",
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def attest(
        self,
        conditions: list[dict[str, Any]],
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        proof: Optional[str] = None,
        format: Optional[str] = None,
    ) -> dict:
        """Create a privacy-preserving on-chain verification.

        Verifies 1-10 conditions (token balances, NFT ownership, EAS
        attestations) and returns a cryptographically signed true/false result.
        Never exposes actual balances. Costs 1 verification credit (standard)
        or 2 credits (with proof="merkle").

        Args:
            conditions: List of condition dicts, each with:
                - type: "token_balance", "nft_ownership", "eas_attestation",
                  "farcaster_id", "evm_view_call", "ratio_to_amount", "ratio_to_supply",
                  "erc8004_agent", or "erc7710_delegation"
                - contractAddress: Token/NFT contract address (for token_balance/nft_ownership/ratio_*).
                  "native" is for token_balance and ratio_to_amount only. nft_ownership
                  needs the NFT contract address (0x + 40 hex on EVM); "native" there is a 400.
                  For XRPL: use r-address issuer for trust line tokens, or "native" for XRP.
                  For Stellar: use the asset issuer's G-address, or "native" for XLM.
                  For Sui: use the full coin type address::module::Name
                  (e.g. "0x...::usdc::USDC"). Native SUI is "0x2::sui::SUI";
                  "native" is not accepted on Sui (400).
                  ratio_to_supply requires an ERC-20 contract (no "native").
                - chainId: EVM chain ID (int, includes 50 for XDC), "solana", "xrpl",
                  "bitcoin", "tron", "stellar", or "sui" (ratio_to_amount and
                  ratio_to_supply are EVM chains only)
                - threshold: Min balance for token_balance, as a decimal string in
                  token/display units (e.g. "1000", not 1000) to preserve full
                  precision. A number is accepted and coerced to a string.
                - multiple: collateralization multiple as a decimal string (for
                  ratio_to_amount; met iff balance >= multiple * amount), e.g. "10"
                - amount: per-request reference amount in token units as a decimal string
                  (for ratio_to_amount, e.g. "100" for 100 USDC, not base units)
                - minFraction: required share of total supply as a decimal string in (0, 1]
                  (for ratio_to_supply, e.g. "0.005" for 0.5%; met iff balance / totalSupply >= minFraction).
                  A number is accepted and coerced to a string for all three.
                - decimals: Optional. Leave it out: the token's own decimals are always
                  read from the chain. If sent it is only a cross-check, and a value that
                  differs from the token's own decimals is rejected with a 400.
                - label: Human-readable label
                - taxon: XRPL NFToken taxon filter (integer, optional)
                - currency: XRPL trust line currency code (e.g. "USD" for RLUSD)
                - assetCode: Stellar trustline asset code (e.g. "USDC", "BENJI"). Required
                  for Stellar non-native tokens. Flows into conditionHash.
                - template: Compliance template name (for eas_attestation, e.g.
                  "coinbase_verified_account", "gitcoin_passport_score", "gitcoin_passport_active")
                - schemaId: EAS schema ID (for eas_attestation, if not using template)
                - attester: Expected attester address (optional, for eas_attestation)
                - indexer: EAS indexer contract (optional, for eas_attestation)
            wallet: EVM wallet address (0x...)
            solana_wallet: Solana wallet address (base58)
            xrpl_wallet: XRPL wallet address (r-address). For verifying XRP,
                trust line tokens (RLUSD, USDC), or NFTs on XRP Ledger.
            bitcoin_wallet: Bitcoin address (P2PKH, P2SH, bech32, or Taproot).
                For verifying native BTC balance. Use chainId "bitcoin" with
                contractAddress "native".
            tron_wallet: Tron wallet address (T-prefixed, base58). For verifying
                TRX or TRC20 tokens (USDT-TRC20). Use chainId "tron".
            stellar_wallet: Stellar wallet address (G-prefixed). For verifying
                XLM or classic trustline assets. Soroban contract balances not
                visible. Use chainId "stellar".
            sui_wallet: Sui wallet address (0x + 64 hex chars). For verifying
                SUI or Sui-native tokens (USDC). Use chainId "sui" with the coin
                type as contractAddress ("0x2::sui::SUI" for native SUI, not "native").
            proof: Set to "merkle" for EIP-1186 Merkle storage proofs.
                Available for token_balance conditions on 27 of the 31 EVM chains
                (not ZKsync Era, Sei, Viction or XDC Network).
                Costs 2 credits. Reveals raw balance to the caller.
            format: Set to "jwt" to include a Wallet Auth by InsumerAPI token
                (ES256-signed JWT) in the response, with its post-quantum
                sibling ``pqJwt`` beside it. Verifiable by any standard
                JWT library using JWKS at /.well-known/jwks.json. No additional cost.

        Returns:
            API response with verification results, ECDSA signature (``sig``),
            and key ID (``kid``) identifying the signing key. Since September
            2026 every response also carries an ML-DSA-65 post-quantum
            companion signature (``pqSig``, ``pqKid``) over the same bytes the
            classical ``kid`` selects; additive, ``sig`` and ``kid`` are
            unchanged. Fetch the public keys via ``get_jwks()`` to verify
            signatures.
            Each result includes ``blockNumber`` and ``blockTimestamp`` (EVM)
            or ``ledgerIndex`` and ``ledgerHash`` (XRPL/Stellar) or
            ``checkpointSequence`` and ``checkpointDigest`` (Sui). The EVM
            block and the XRPL ledger name the state read, the Solana slot is
            a floor, and the Bitcoin, Tron, Stellar and Sui anchors are tip
            markers (freshness anchors). XRPL trust
            line token results also include ``trustLineState: { frozen: bool }``:
            a frozen trust line causes ``met: false`` regardless of balance.
            Stellar non-native results surface ``assetCode`` in ``evaluatedCondition``.
            When format="jwt", response includes a ``jwt`` field with a
            Wallet Auth by InsumerAPI token (ES256-signed JWT).
            When proof="merkle", each result includes a proof object with
            accountProof, storageProof, storageHash, blockNumber, and
            mappingSlot fields.
        """
        # v2 keys require agent-supplied quantities as decimal strings (preserving full
        # precision, no float in signed bytes); v1 keys accept either. Coerce numbers to
        # strings so the request works on any key. Other condition fields are untouched.
        #   token_balance.threshold, ratio_to_amount.multiple/amount, ratio_to_supply.minFraction.
        # NOTE: str() — NOT the builtin format(), which is shadowed by the `format` parameter.
        _str_fields = {
            "token_balance": ("threshold",),
            "ratio_to_amount": ("multiple", "amount"),
            "ratio_to_supply": ("minFraction",),
        }
        norm_conditions: list[dict[str, Any]] = []
        for c in conditions:
            if isinstance(c, dict):
                fields = _str_fields.get(c.get("type"))
                if fields:
                    updates = {
                        f: _decimal_str(c[f])
                        for f in fields
                        if c.get(f) is not None and not isinstance(c[f], str)
                    }
                    if updates:
                        c = {**c, **updates}
            norm_conditions.append(c)
        body: dict[str, Any] = {"conditions": norm_conditions}
        if wallet:
            body["wallet"] = wallet
        if solana_wallet:
            body["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            body["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            body["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            body["tronWallet"] = tron_wallet
        if stellar_wallet:
            body["stellarWallet"] = stellar_wallet
        if sui_wallet:
            body["suiWallet"] = sui_wallet
        if proof:
            body["proof"] = proof
        if format:
            body["format"] = format
        return self._post("/attest", body)

    def wallet_trust(
        self,
        wallet: str,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        proof: Optional[str] = None,
    ) -> dict:
        """Generate a structured wallet trust fact profile.

        Checks 145 base conditions across 27 chains in 9 dimensions: stablecoins
        (52: USDC, USDT, OUSD, PYUSD, USDG, USD1, RLUSD, USDS, DAI, EURC on 23
        EVM chains), governance tokens (8: UNI, AAVE, ARB, OP, ENS, LDO, SKY,
        COMP), NFTs (3), staking positions (5: stETH, rETH, cbETH, wstETH,
        weETH), institutional stablecoins (8: EURCV and USDCV on Ethereum and
        Solana, EURCV on XRPL, USDC and BENJI on Stellar, USDC on Sui),
        tokenized treasuries (16: BUIDL, USYC, OUSG, USTB, USDY), stablecoin
        deposits (39: Aave v3 aUSDC/aUSDT, sUSDS, sDAI, listed Morpho USDC
        vaults), wrapped bitcoin (12: cbBTC, WBTC, tBTC) and names (2: ENS
        .eth, Basenames). Up to 166 checks across 29 chains in 13 dimensions
        with the optional Solana (14), XRPL (3), Bitcoin (1) and Tron (3)
        wallets; Stellar and Sui wallets add no dimension but let their rows
        inside the base dimensions evaluate. Every check is a presence check. A
        check whose chain wallet was not supplied stays in the signed profile
        with ``evaluated: false`` and ``reason: "wallet_not_provided"``, counted
        in ``notEvaluatedCount`` rather than passed or failed. The signed
        ``conditionSetVersion`` (currently ``"2026-10"``) names the check list
        that was run; log it, never reject on it. Returns per-dimension
        pass/fail counts and an overall summary.
        No score, just cryptographically verifiable evidence. Costs 3 credits
        (standard) or 6 credits (with proof="merkle").

        Args:
            wallet: EVM wallet address (0x...) to profile.
            solana_wallet: Solana wallet address (base58). Adds the 14-check
                solana dimension (USDC, EURC, OUSD, PYUSD, USD1, USDG, USDS,
                BUIDL, USDY, WBTC, cbBTC, tBTC, JitoSOL, mSOL) and lets the
                institutional EURCV/USDCV on Solana rows evaluate.
            xrpl_wallet: XRPL wallet address (r-address). Adds the xrpl
                dimension (RLUSD, USDC, OUSG) and lets the institutional EURCV
                on XRPL row evaluate.
            bitcoin_wallet: Bitcoin address. Adds the bitcoin dimension (one
                native BTC presence check).
            tron_wallet: Tron wallet address (T-prefixed). Adds the tron
                dimension (USDT, USD1, WBTC on Tron).
            stellar_wallet: Stellar wallet address (G-prefixed). Adds no
                dimension; lets the institutional USDC and BENJI on Stellar rows
                evaluate (classic trustlines).
            sui_wallet: Sui wallet address (0x + 64 hex). Adds no dimension;
                lets the institutional USDC on Sui and tokenized-treasury USDY
                on Sui rows evaluate.
            proof: Set to "merkle" for EIP-1186 Merkle storage proofs on EVM
                token checks, on 27 of the 31 EVM chains (not ZKsync Era, Sei,
                Viction or XDC Network). Rows whose balance is computed rather
                than stored (Aave aTokens, BUIDL), NFT rows and non-EVM rows are
                declined with a reason; the premium is refunded whenever no
                proof is delivered. Costs 6 credits.

        Returns:
            API response with trust profile, ECDSA signature (``sig``),
            key ID (``kid``, ``insumer-trust-v2`` on current keys), and the
            ML-DSA-65 post-quantum companion (``pqSig``, ``pqKid``
            ``insumer-trust-pq1``) carried since September 2026.
        """
        body: dict[str, Any] = {"wallet": wallet}
        if solana_wallet:
            body["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            body["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            body["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            body["tronWallet"] = tron_wallet
        if stellar_wallet:
            body["stellarWallet"] = stellar_wallet
        if sui_wallet:
            body["suiWallet"] = sui_wallet
        if proof:
            body["proof"] = proof
        return self._post("/trust", body)

    def batch_wallet_trust(
        self,
        wallets: list[dict[str, Any]],
        proof: Optional[str] = None,
    ) -> dict:
        """Generate wallet trust fact profiles for up to 10 wallets in one request.

        Shared block fetches make this 5-8x faster than sequential
        ``wallet_trust()`` calls. Each wallet gets an independently
        ECDSA-signed profile. Supports partial success — failed wallets get
        error entries while successful ones return full profiles. Credits
        only charged for successful profiles.

        Args:
            wallets: List of 1-10 dicts, each with ``wallet`` (EVM address,
                required) and optional ``solanaWallet`` (base58),
                ``xrplWallet`` (r-address), ``bitcoinWallet``, ``tronWallet``
                (T-prefixed), ``stellarWallet`` (G-prefixed), and ``suiWallet``
                (0x + 64 hex).
            proof: Set to ``"merkle"`` for EIP-1186 Merkle storage proofs.
                Costs 6 credits per wallet instead of 3.

        Returns:
            API response with ``results`` array (success/error entries),
            ``summary`` (requested/succeeded/failed counts), and ``meta``
            (creditsCharged, creditsRemaining).
        """
        body: dict[str, Any] = {"wallets": wallets}
        if proof:
            body["proof"] = proof
        return self._post("/trust/batch", body)

    def get_credits(self) -> dict:
        """Check verification credit balance for the API key."""
        return self._get("/credits")

    def list_merchants(
        self,
        token: Optional[str] = None,
        verified: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List merchants in the public directory. No authentication required."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if token:
            params["token"] = token
        if verified is not None:
            params["verified"] = str(verified).lower()
        resp = requests.get(
            f"{BASE_URL}/merchants",
            params=params,
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def get_merchant(self, merchant_id: str) -> dict:
        """Get full public merchant profile with tier structures. No authentication required."""
        resp = requests.get(
            f"{BASE_URL}/merchants/{merchant_id}",
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def list_tokens(
        self,
        chain: Optional[Any] = None,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> dict:
        """List registered tokens and NFT collections. No authentication required."""
        params: dict[str, Any] = {}
        if chain is not None:
            params["chain"] = chain
        if symbol:
            params["symbol"] = symbol
        if asset_type:
            params["type"] = asset_type
        resp = requests.get(
            f"{BASE_URL}/tokens",
            params=params,
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def check_discount(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
    ) -> dict:
        """Calculate discount for a wallet at a merchant. No authentication required. Free, no credits consumed."""
        params: dict[str, Any] = {"merchant": merchant_id}
        if wallet:
            params["wallet"] = wallet
        if solana_wallet:
            params["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            params["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            params["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            params["tronWallet"] = tron_wallet
        if stellar_wallet:
            params["stellarWallet"] = stellar_wallet
        if sui_wallet:
            params["suiWallet"] = sui_wallet
        resp = requests.get(
            f"{BASE_URL}/discount/check",
            params=params,
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()

    def verify(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
    ) -> dict:
        """Create a signed discount code (INSR-XXXXX), valid 30 minutes. Costs 1 credit."""
        body: dict[str, Any] = {"merchantId": merchant_id}
        if wallet:
            body["wallet"] = wallet
        if solana_wallet:
            body["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            body["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            body["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            body["tronWallet"] = tron_wallet
        if stellar_wallet:
            body["stellarWallet"] = stellar_wallet
        if sui_wallet:
            body["suiWallet"] = sui_wallet
        return self._post("/verify", body)

    def buy_key(
        self,
        tx_hash: str,
        chain_id: Any,
        amount: float,
        app_name: str,
    ) -> dict:
        """Buy a new API key with USDC, USDT, or BTC (no auth required). Wallet becomes the key identity."""
        return self._public_post("/keys/buy", {
            "txHash": tx_hash,
            "chainId": chain_id,
            "amount": amount,
            "appName": app_name,
        })

    def buy_credits(
        self,
        tx_hash: str,
        chain_id: Any,
        amount: Optional[float] = None,
        update_wallet: bool = False,
    ) -> dict:
        """Buy verification credits with USDC, USDT, or BTC. Rate: 25 credits per $1. Minimum 5."""
        body: dict = {
            "txHash": tx_hash,
            "chainId": chain_id,
        }
        if amount is not None:
            body["amount"] = amount
        if update_wallet:
            body["updateWallet"] = True
        return self._post("/credits/buy", body)

    def confirm_payment(
        self,
        code: str,
        tx_hash: str,
        chain_id: Any,
        amount: Any,
    ) -> dict:
        """Confirm USDC payment for a discount code. Server verifies the transaction."""
        return self._post("/payment/confirm", {
            "code": code,
            "txHash": tx_hash,
            "chainId": chain_id,
            "amount": amount,
        })

    def create_merchant(
        self,
        company_name: str,
        company_id: str,
        location: Optional[str] = None,
    ) -> dict:
        """Create a new merchant. Receives 100 free verification credits. Max 10 per API key."""
        body: dict[str, Any] = {
            "companyName": company_name,
            "companyId": company_id,
        }
        if location:
            body["location"] = location
        return self._post("/merchants", body)

    def get_merchant_status(self, merchant_id: str) -> dict:
        """Get full private merchant details: credits, configs, directory status. Owner only."""
        return self._get(f"/merchants/{merchant_id}/status")

    def configure_tokens(
        self,
        merchant_id: str,
        own_token: Optional[dict] = None,
        partner_tokens: Optional[list] = None,
    ) -> dict:
        """Configure merchant token discount tiers. Max 8 tokens total. Owner only."""
        body: dict[str, Any] = {}
        if own_token is not None:
            body["ownToken"] = own_token
        if partner_tokens is not None:
            body["partnerTokens"] = partner_tokens
        return self._put(f"/merchants/{merchant_id}/tokens", body)

    def configure_nfts(
        self,
        merchant_id: str,
        nft_collections: list,
    ) -> dict:
        """Configure NFT collections that grant discounts. Max 4 collections. Owner only."""
        return self._put(f"/merchants/{merchant_id}/nfts", {
            "nftCollections": nft_collections,
        })

    def configure_settings(
        self,
        merchant_id: str,
        discount_mode: Optional[str] = None,
        discount_cap: Optional[int] = None,
        usdc_payment: Optional[dict] = None,
    ) -> dict:
        """Update merchant settings: discount mode, cap, USDC payments. Owner only."""
        body: dict[str, Any] = {}
        if discount_mode is not None:
            body["discountMode"] = discount_mode
        if discount_cap is not None:
            body["discountCap"] = discount_cap
        if usdc_payment is not None:
            body["usdcPayment"] = usdc_payment
        return self._put(f"/merchants/{merchant_id}/settings", body)

    def publish_directory(self, merchant_id: str) -> dict:
        """Publish or refresh merchant listing in the public directory. Owner only."""
        return self._post(f"/merchants/{merchant_id}/directory", {})

    def buy_merchant_credits(
        self,
        merchant_id: str,
        tx_hash: str,
        chain_id: Any,
        amount: Optional[float] = None,
        update_wallet: bool = False,
    ) -> dict:
        """Buy merchant verification credits with USDC, USDT, or BTC. Rate: 25 credits per $1. Min 5. Owner only."""
        body: dict = {
            "txHash": tx_hash,
            "chainId": chain_id,
        }
        if amount is not None:
            body["amount"] = amount
        if update_wallet:
            body["updateWallet"] = True
        return self._post(f"/merchants/{merchant_id}/credits", body)

    def acp_discount(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        items: Optional[list] = None,
    ) -> dict:
        """Check discount eligibility in ACP (OpenAI/Stripe Agentic Commerce Protocol) format.

        Returns coupon objects, applied/rejected arrays, and per-item allocations
        compatible with ACP checkout flows. Same verification as ``verify()``,
        wrapped in ACP format. Costs 1 merchant credit.

        Args:
            merchant_id: Merchant identifier.
            wallet: EVM wallet address (0x...).
            solana_wallet: Solana wallet address (base58).
            xrpl_wallet: XRPL wallet address (r-address).
            bitcoin_wallet: Bitcoin address.
            tron_wallet: Tron wallet address (T-prefixed).
            stellar_wallet: Stellar wallet address (G-prefixed).
            sui_wallet: Sui wallet address (0x + 64 hex).
            items: Optional line items for per-item allocations. Each dict has
                ``path`` (JSONPath, e.g. '$.line_items[0]') and ``amount`` (cents).

        Returns:
            ACP-format response with discounts.applied, discounts.rejected,
            coupon objects, and ECDSA-signed verification block.
        """
        body: dict[str, Any] = {"merchantId": merchant_id}
        if wallet:
            body["wallet"] = wallet
        if solana_wallet:
            body["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            body["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            body["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            body["tronWallet"] = tron_wallet
        if stellar_wallet:
            body["stellarWallet"] = stellar_wallet
        if sui_wallet:
            body["suiWallet"] = sui_wallet
        if items is not None:
            body["items"] = items
        return self._post("/acp/discount", body)

    def ucp_discount(
        self,
        merchant_id: str,
        wallet: Optional[str] = None,
        solana_wallet: Optional[str] = None,
        xrpl_wallet: Optional[str] = None,
        bitcoin_wallet: Optional[str] = None,
        tron_wallet: Optional[str] = None,
        stellar_wallet: Optional[str] = None,
        sui_wallet: Optional[str] = None,
        items: Optional[list] = None,
    ) -> dict:
        """Check discount eligibility in UCP (Google Universal Commerce Protocol) format.

        Returns title, extension field, and applied array compatible with UCP
        checkout flows. Same verification as ``verify()``, wrapped in UCP format.
        Costs 1 merchant credit.

        Args:
            merchant_id: Merchant identifier.
            wallet: EVM wallet address (0x...).
            solana_wallet: Solana wallet address (base58).
            xrpl_wallet: XRPL wallet address (r-address).
            bitcoin_wallet: Bitcoin address.
            tron_wallet: Tron wallet address (T-prefixed).
            stellar_wallet: Stellar wallet address (G-prefixed).
            sui_wallet: Sui wallet address (0x + 64 hex).
            items: Optional line items for per-item allocations. Each dict has
                ``path`` (JSONPath, e.g. '$.line_items[0]') and ``amount`` (cents).

        Returns:
            UCP-format response with discounts.applied, extension field,
            and ECDSA-signed verification block.
        """
        body: dict[str, Any] = {"merchantId": merchant_id}
        if wallet:
            body["wallet"] = wallet
        if solana_wallet:
            body["solanaWallet"] = solana_wallet
        if xrpl_wallet:
            body["xrplWallet"] = xrpl_wallet
        if bitcoin_wallet:
            body["bitcoinWallet"] = bitcoin_wallet
        if tron_wallet:
            body["tronWallet"] = tron_wallet
        if stellar_wallet:
            body["stellarWallet"] = stellar_wallet
        if sui_wallet:
            body["suiWallet"] = sui_wallet
        if items is not None:
            body["items"] = items
        return self._post("/ucp/discount", body)

    def request_domain_verification(
        self,
        merchant_id: str,
        domain: str,
    ) -> dict:
        """Request a domain verification token for a merchant.

        Returns a token and three verification methods (DNS TXT record,
        HTML meta tag, or file upload). After placing the token, call
        ``verify_domain()`` to complete verification. Owner only.

        Args:
            merchant_id: Merchant identifier.
            domain: Domain to verify (e.g. 'example.com').

        Returns:
            Verification token and instructions for all three methods.
        """
        return self._post(f"/merchants/{merchant_id}/domain-verification", {
            "domain": domain,
        })

    def verify_domain(self, merchant_id: str) -> dict:
        """Verify domain ownership for a merchant.

        Call after placing the verification token (from
        ``request_domain_verification()``) via DNS TXT, meta tag, or file.
        The server checks all three methods automatically. Rate limited
        to 5 attempts per hour. Owner only.

        Args:
            merchant_id: Merchant identifier.

        Returns:
            Verification result with ``verified`` (bool), ``domain``,
            and ``method`` (if successful) or ``attemptsRemaining``.
        """
        return self._put(f"/merchants/{merchant_id}/domain-verification")

    def validate_code(self, code: str) -> dict:
        """Validate an INSR-XXXXX discount code.

        For merchant backends during ACP/UCP checkout to confirm code validity,
        discount percent, and expiry. No authentication required, no credits
        consumed. Does not expose wallet or token data.

        Args:
            code: Discount code in INSR-XXXXX format.

        Returns:
            Validation result with ``valid`` (bool), ``code``, and either
            merchant/discount details (if valid) or ``reason`` (if invalid).
        """
        resp = requests.get(
            f"{BASE_URL}/codes/{code}",
            timeout=self.timeout,
        )
        _raise_for_status(resp)
        return resp.json()
