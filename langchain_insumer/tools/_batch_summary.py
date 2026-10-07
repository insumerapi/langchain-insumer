"""Summary text for batch trust responses.

A batch trust response carries up to ten complete signed profiles, tens of
thousands of characters each, which is more than a model can read from one
tool result. summarize_batch_trust turns the response into a short text for
the model: per wallet, the profile ID, the held / not held / not evaluated
counts, and the checks held in each dimension (present, for the account
dimension, whose checks are code states rather than holdings). Dimensions are
printed in a fixed order, the API's own, whatever order they arrive in, so two
wallets in one batch always read alike. The signed profiles are not changed;
the tool returns them unchanged as the tool message's artifact.
"""

from typing import Any, Dict, List, Optional

# The API's dimension order: the base dimensions, then the optional ones that
# were switched on. Any name outside this list follows, alphabetically.
DIMENSION_ORDER = (
    "stablecoins",
    "governance",
    "nfts",
    "staking",
    "institutional_stablecoins",
    "tokenized_treasuries",
    "stablecoin_deposits",
    "wrapped_bitcoin",
    "names",
    "account",
    "solana",
    "xrpl",
    "bitcoin",
    "tron",
)

# Dimensions whose checks are states of the account, not holdings: the summary
# says "present" for them, "held" for every other dimension.
_PRESENT_DIMENSIONS = frozenset({"account"})


def _str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _is_signed(entry: dict) -> bool:
    sig, kid = entry.get("sig"), entry.get("kid")
    return isinstance(entry.get("trust"), dict) and isinstance(sig, str) and bool(sig) and isinstance(kid, str) and bool(kid)


def _paid_per_call(meta: dict) -> bool:
    # The API returns creditsCharged 0 and creditsRemaining null when the call
    # was paid per call with x402. That payment covers every wallet requested.
    return "creditsRemaining" in meta and meta["creditsRemaining"] is None and meta.get("creditsCharged") == 0


def _ordered_dimensions(dims: Dict[str, Any]) -> List[str]:
    """Dimension names in the fixed order, regardless of the order received."""
    rank = {name: i for i, name in enumerate(DIMENSION_ORDER)}
    known = [name for name in dims if name in rank]
    other = [name for name in dims if name not in rank]
    return sorted(known, key=rank.__getitem__) + sorted(other)


def _dimension_line(name: str, dim: dict) -> str:
    raw = dim.get("checks")
    checks = [c for c in raw if isinstance(c, dict)] if isinstance(raw, list) else []
    met = [_str(c.get("label")) for c in checks if c.get("met") is True]
    not_evaluated = sum(1 for c in checks if c.get("evaluated") is False)
    total = dim.get("total") if isinstance(dim.get("total"), int) and not isinstance(dim.get("total"), bool) else len(checks)
    word = "present" if name in _PRESENT_DIMENSIONS else "held"
    line = f"   {name}: {len(met)} of {total} {word}"
    if not_evaluated > 0:
        line += f" ({not_evaluated} not evaluated)"
    if met:
        line += ": " + ", ".join(met)
    return line


def _held_line(summary: dict, dims: dict) -> str:
    """Asset rows held, with the account dimension's facts counted beside them, never added.

    A profile without an account dimension keeps the plain count.
    """
    account = dims.get("account") if isinstance(dims.get("account"), dict) else None
    present = account.get("passCount") if account else None
    total_passed = summary.get("totalPassed")
    if not (isinstance(present, int) and not isinstance(present, bool)) or not (isinstance(total_passed, int) and not isinstance(total_passed, bool)) or total_passed < present:
        return f"{_str(total_passed)} held"
    return f"{total_passed - present} assets held, {present} account facts present"


def _profile_lines(index: int, entry: dict, trust: dict) -> List[str]:
    summary = trust.get("summary") if isinstance(trust.get("summary"), dict) else {}
    dims = trust.get("dimensions") if isinstance(trust.get("dimensions"), dict) else {}
    if _is_signed(entry):
        kid = entry["kid"]
        pq = f" + {_str(entry.get('pqKid'))}" if entry.get("pqKid") and entry.get("pqSig") else ""
        signature = f"signed ({kid}{pq})"
    else:
        signature = "returned without a signature: do not rely on it"
    lines = [
        f"{index}. {_str(trust.get('wallet'))} · {_str(trust.get('id'))} · check set {_str(trust.get('conditionSetVersion'))} · expires {_str(trust.get('expiresAt'))} · {signature}",
        f"   {_str(summary.get('totalChecks'))} checks: {_held_line(summary, dims)}, {_str(summary.get('totalFailed'))} not held, {_str(summary.get('totalNotEvaluated'))} not evaluated",
    ]
    for name in _ordered_dimensions(dims):
        dim = dims[name]
        if isinstance(dim, dict):
            lines.append(_dimension_line(name, dim))
    return lines


def _error_lines(index: int, entry: dict, per_call: bool) -> List[str]:
    raw = entry.get("error")
    err = raw if isinstance(raw, dict) else {}
    reason = _str(err.get("message")) or _str(err.get("code")) or (raw if isinstance(raw, str) else "no reason given")
    charge = "The per-call payment covered this wallet too." if per_call else "No credits were charged for it."
    return [
        f"{index}. {_str(err.get('wallet')) or '(wallet not named)'} · not signed: {reason}",
        f"   No profile was signed for this wallet. {charge} Retry this wallet; never read this entry as a no.",
    ]


def summarize_batch_trust(response: Any) -> Optional[str]:
    """Return a summary of a /v1/trust/batch response, or None when it carries no results list."""
    if not isinstance(response, dict):
        return None
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    results = data.get("results")
    if not isinstance(results, list):
        return None
    meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
    counts = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    signed_count = sum(1 for e in results if isinstance(e, dict) and _is_signed(e))

    def count(key: str, fallback: int) -> Any:
        value = counts.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else fallback

    requested = count("requested", len(results))
    # Signed means a profile with a signature and a kid, whatever the API's own success
    # count says: a profile returned without them is not counted as signed.
    succeeded = signed_count
    failed = len(results) - signed_count
    per_call = _paid_per_call(meta)
    charge = (
        "Paid per call: the payment covered every wallet requested."
        if per_call
        else f"Credits charged: {_str(meta.get('creditsCharged'))}."
    )
    out = [
        f"Batch trust profiles: {requested} requested, {succeeded} signed, {failed} not signed. {charge}",
        "This text is a summary for reading. Each signed profile (trust object, sig and kid, pqSig and pqKid) is in this tool result's artifact, unchanged, and verifies against the InsumerAPI JWKS. Profiles cannot be fetched again, so a new call with detail=\"full\" signs fresh profiles and is charged again.",
        "Every check is held or not held (present or not present for the account dimension: contract code or an EIP-7702 delegation at the address), never a balance and never the code. The counts are facts about the wallet, not a score; the account facts are counted beside the assets, never added to them.",
        "",
    ]
    for i, entry in enumerate(results, start=1):
        e = entry if isinstance(entry, dict) else {}
        trust = e.get("trust")
        out.extend(_profile_lines(i, e, trust) if isinstance(trust, dict) else _error_lines(i, e, per_call))
        out.append("")
    return "\n".join(out).rstrip()
