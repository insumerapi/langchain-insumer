"""Tests for langchain-insumer tools."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from langchain_insumer import (
    InsumerAPIWrapper,
    InsumerAttestTool,
    InsumerBatchWalletTrustTool,
    InsumerCheckDiscountTool,
    InsumerCreditsTool,
    InsumerListMerchantsTool,
    InsumerListTokensTool,
    InsumerVerifyTool,
)


@pytest.fixture
def api():
    return InsumerAPIWrapper(api_key="insr_live_0000000000000000000000000000000000000000")


@pytest.fixture
def mock_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "ok": True,
        "data": {},
        "meta": {"version": "1.0", "timestamp": "2026-02-22T00:00:00.000Z"},
    }
    mock.raise_for_status = MagicMock()
    return mock


class TestInsumerAPIWrapper:
    def test_headers(self, api):
        headers = api._headers()
        assert headers["X-API-Key"] == "insr_live_0000000000000000000000000000000000000000"
        assert headers["Content-Type"] == "application/json"

    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest(self, mock_post, api, mock_response):
        mock_response.json.return_value = {
            "ok": True,
            "data": {
                "attestation": {
                    "id": "ATST-A7C3E1B2D4F56789",
                    "pass": True,
                    "results": [{"condition": 0, "met": True}],
                    "passCount": 1,
                    "failCount": 0,
                },
                "sig": "base64sig...",
                "kid": "insumer-attest-v1",
            },
            "meta": {"creditsRemaining": 9},
        }
        mock_post.return_value = mock_response

        result = api.attest(
            wallet="0x1234567890abcdef1234567890abcdef12345678",
            conditions=[
                {
                    "type": "token_balance",
                    "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "chainId": 1,
                    "threshold": 100,
                    "decimals": 6,
                }
            ],
        )

        assert result["ok"] is True
        assert result["data"]["attestation"]["pass"] is True
        mock_post.assert_called_once()

    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest_without_format(self, mock_post, api, mock_response):
        """attest without format — response unchanged, no jwt field."""
        mock_response.json.return_value = {
            "ok": True,
            "data": {
                "attestation": {
                    "id": "ATST-A7C3E1B2D4F56789",
                    "pass": True,
                    "results": [{"condition": 0, "met": True}],
                    "passCount": 1,
                    "failCount": 0,
                },
                "sig": "base64sig...",
                "kid": "insumer-attest-v1",
            },
            "meta": {"creditsRemaining": 9},
        }
        mock_post.return_value = mock_response

        result = api.attest(
            wallet="0x1234567890abcdef1234567890abcdef12345678",
            conditions=[{"type": "token_balance", "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "chainId": 1, "threshold": 100, "decimals": 6}],
        )

        assert result["ok"] is True
        assert "jwt" not in result["data"]
        # Verify format was NOT sent in the request body
        call_kwargs = mock_post.call_args
        sent_body = call_kwargs.kwargs.get("json", {})
        assert "format" not in sent_body

    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest_with_jwt_format(self, mock_post, api, mock_response):
        """attest with format='jwt' — jwt field present in response."""
        mock_response.json.return_value = {
            "ok": True,
            "data": {
                "attestation": {
                    "id": "ATST-B8D4F6A7E9C01234",
                    "pass": True,
                    "results": [{"condition": 0, "met": True}],
                    "passCount": 1,
                    "failCount": 0,
                },
                "sig": "base64sig...",
                "kid": "insumer-attest-v1",
                "jwt": "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIweDEyMzQifQ.dGVzdA",
            },
            "meta": {"creditsRemaining": 8},
        }
        mock_post.return_value = mock_response

        result = api.attest(
            wallet="0x1234567890abcdef1234567890abcdef12345678",
            conditions=[{"type": "token_balance", "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "chainId": 1, "threshold": 100, "decimals": 6}],
            format="jwt",
        )

        assert result["ok"] is True
        assert "jwt" in result["data"]
        jwt_val = result["data"]["jwt"]
        # JWT is three dot-separated base64 segments
        parts = jwt_val.split(".")
        assert len(parts) == 3
        assert all(len(p) > 0 for p in parts)
        # Verify format was sent in the request body
        call_kwargs = mock_post.call_args
        sent_body = call_kwargs.kwargs.get("json", {})
        assert sent_body.get("format") == "jwt"

    @patch("langchain_insumer.wrapper.requests.get")
    def test_get_credits(self, mock_get, api, mock_response):
        mock_response.json.return_value = {
            "ok": True,
            "data": {"apiKeyCredits": 42, "tier": "pro", "dailyLimit": 10000},
        }
        mock_get.return_value = mock_response

        result = api.get_credits()
        assert result["data"]["apiKeyCredits"] == 42

    @patch("langchain_insumer.wrapper.requests.get")
    def test_list_merchants(self, mock_get, api, mock_response):
        mock_response.json.return_value = {
            "ok": True,
            "data": [{"id": "test", "companyName": "Test Co"}],
            "meta": {"total": 1, "limit": 50, "offset": 0},
        }
        mock_get.return_value = mock_response

        result = api.list_merchants(token="UNI", limit=10)
        assert len(result["data"]) == 1

    @patch("langchain_insumer.wrapper.requests.get")
    def test_check_discount(self, mock_get, api, mock_response):
        mock_response.json.return_value = {
            "ok": True,
            "data": {"eligible": True, "totalDiscount": 15},
        }
        mock_get.return_value = mock_response

        result = api.check_discount(
            merchant_id="test",
            wallet="0x1234567890abcdef1234567890abcdef12345678",
        )
        assert result["data"]["totalDiscount"] == 15


def _error_response(status, json_body=None):
    resp = requests.Response()
    resp.status_code = status
    resp.reason = "Error"
    resp.url = "https://api.insumermodel.com/v1/attest"
    if json_body is None:
        resp._content = b"<html>upstream error</html>"
    else:
        resp._content = json.dumps(json_body).encode()
    return resp


class TestErrorSurfacing:
    @patch("langchain_insumer.wrapper.requests.post")
    def test_400_message_is_surfaced(self, mock_post, api):
        message = "decimals does not match the token: the token reports 6"
        mock_post.return_value = _error_response(
            400, {"ok": False, "error": {"code": "invalid_request", "message": message}}
        )

        with pytest.raises(requests.HTTPError) as excinfo:
            api.attest(
                wallet="0x1234567890abcdef1234567890abcdef12345678",
                conditions=[{"type": "token_balance", "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "chainId": 1, "threshold": "100", "decimals": 18}],
            )

        assert message in str(excinfo.value)
        assert "400" in str(excinfo.value)
        assert excinfo.value.response.status_code == 400

    @patch("langchain_insumer.wrapper.requests.post")
    def test_503_lists_failed_conditions(self, mock_post, api):
        mock_post.return_value = _error_response(
            503,
            {
                "ok": False,
                "error": {
                    "code": "rpc_failure",
                    "message": "Unable to read one or more data sources",
                    "failedConditions": [{"condition": 0, "chainId": "sui", "source": "balance_read"}],
                },
            },
        )

        with pytest.raises(requests.HTTPError) as excinfo:
            api.wallet_trust(wallet="0x1234567890abcdef1234567890abcdef12345678")

        text = str(excinfo.value)
        assert "rpc_failure" in text
        assert "failedConditions" in text
        assert "balance_read" in text
        assert excinfo.value.response.status_code == 503

    @patch("langchain_insumer.wrapper.requests.get")
    def test_non_json_body_falls_back_to_status_error(self, mock_get, api):
        mock_get.return_value = _error_response(502)

        with pytest.raises(requests.HTTPError) as excinfo:
            api.get_credits()

        assert "502" in str(excinfo.value)
        assert excinfo.value.response.status_code == 502

    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest_tool_raises_with_message(self, mock_post, api):
        message = "Sui contractAddress must be a coin type (address::module::Name)"
        mock_post.return_value = _error_response(
            400, {"ok": False, "error": {"code": "invalid_request", "message": message}}
        )

        tool = InsumerAttestTool(api_wrapper=api)
        with pytest.raises(requests.HTTPError, match="coin type"):
            tool._run(
                conditions=json.dumps([{"type": "token_balance", "contractAddress": "native", "chainId": "sui", "threshold": "1"}]),
                sui_wallet="0x" + "ab" * 32,
            )


class TestTools:
    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest_tool(self, mock_post, api, mock_response):
        mock_response.json.return_value = {
            "ok": True,
            "data": {"attestation": {"pass": True}},
        }
        mock_post.return_value = mock_response

        tool = InsumerAttestTool(api_wrapper=api)
        assert tool.name == "insumer_attest"

        result = tool._run(
            conditions=json.dumps([{"type": "token_balance", "contractAddress": "0x...", "chainId": 1, "threshold": 100}]),
            wallet="0x1234567890abcdef1234567890abcdef12345678",
        )
        parsed = json.loads(result)
        assert parsed["ok"] is True

    @patch("langchain_insumer.wrapper.requests.post")
    def test_attest_tool_with_jwt_format(self, mock_post, api, mock_response):
        """InsumerAttestTool passes format parameter through."""
        mock_response.json.return_value = {
            "ok": True,
            "data": {
                "attestation": {"pass": True},
                "jwt": "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIweDEyMzQifQ.dGVzdA",
            },
        }
        mock_post.return_value = mock_response

        tool = InsumerAttestTool(api_wrapper=api)
        result = tool._run(
            conditions=json.dumps([{"type": "token_balance", "contractAddress": "0x...", "chainId": 1, "threshold": 100}]),
            wallet="0x1234567890abcdef1234567890abcdef12345678",
            format="jwt",
        )
        parsed = json.loads(result)
        assert parsed["ok"] is True
        assert "jwt" in parsed["data"]

    def test_credits_tool_name(self, api):
        tool = InsumerCreditsTool(api_wrapper=api)
        assert tool.name == "insumer_credits"

    def test_list_merchants_tool_name(self, api):
        tool = InsumerListMerchantsTool(api_wrapper=api)
        assert tool.name == "insumer_list_merchants"

    def test_list_tokens_tool_name(self, api):
        tool = InsumerListTokensTool(api_wrapper=api)
        assert tool.name == "insumer_list_tokens"

    def test_check_discount_tool_name(self, api):
        tool = InsumerCheckDiscountTool(api_wrapper=api)
        assert tool.name == "insumer_check_discount"

    def test_verify_tool_name(self, api):
        tool = InsumerVerifyTool(api_wrapper=api)
        assert tool.name == "insumer_verify"


class TestUnreadMerchantWallets:
    """The merchant endpoints read wallet, solanaWallet and xrplWallet only."""

    @patch("langchain_insumer.wrapper.requests.post")
    def test_post_methods_warn_and_do_not_send(self, mock_post, api, mock_response):
        mock_response.json.return_value = {"ok": True, "data": {}}
        mock_post.return_value = mock_response
        for method in (api.verify, api.acp_discount, api.ucp_discount):
            with pytest.warns(DeprecationWarning, match="wallet, solanaWallet and xrplWallet"):
                method(
                    merchant_id="acme",
                    wallet="0x" + "ab" * 20,
                    bitcoin_wallet="bc1qexample",
                    tron_wallet="Texample",
                    stellar_wallet="Gexample",
                    sui_wallet="0x" + "ab" * 32,
                )
            body = mock_post.call_args.kwargs["json"]
            assert body["wallet"] == "0x" + "ab" * 20
            for key in ("bitcoinWallet", "tronWallet", "stellarWallet", "suiWallet"):
                assert key not in body

    @patch("langchain_insumer.wrapper.requests.get")
    def test_check_discount_warns_and_does_not_send(self, mock_get, api, mock_response):
        mock_response.json.return_value = {"ok": True, "data": {}}
        mock_get.return_value = mock_response
        with pytest.warns(DeprecationWarning, match="sui_wallet"):
            api.check_discount(merchant_id="acme", xrpl_wallet="rExample", sui_wallet="0x" + "ab" * 32)
        params = mock_get.call_args.kwargs["params"]
        assert params == {"merchant": "acme", "xrplWallet": "rExample"}

    @patch("langchain_insumer.wrapper.requests.get")
    def test_no_warning_without_them(self, mock_get, api, mock_response, recwarn):
        mock_response.json.return_value = {"ok": True, "data": {}}
        mock_get.return_value = mock_response
        api.check_discount(merchant_id="acme", wallet="0x" + "ab" * 20)
        assert not [w for w in recwarn if issubclass(w.category, DeprecationWarning)]


def _row(label, met, **extra):
    return {"label": label, "chainId": 1, "met": met, "conditionHash": "0x00", **extra}


BATCH = {
    "ok": True,
    "data": {
        "results": [
            {
                "trust": {
                    "id": "TRST-AAAAA",
                    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                    "conditionSetVersion": "2026-10",
                    "expiresAt": "2026-10-07T19:32:38.129Z",
                    "dimensions": {
                        "stablecoins": {"checks": [_row("USDC on Ethereum", True), _row("USDT on Ethereum", False)], "total": 2},
                        "institutional_stablecoins": {"checks": [_row("USDC on Solana", False, evaluated=False)], "total": 1},
                    },
                    "summary": {"totalChecks": 3, "totalPassed": 1, "totalFailed": 1, "totalNotEvaluated": 1},
                },
                "sig": "c2ln",
                "kid": "insumer-trust-v2",
                "pqSig": "cHE=",
                "pqKid": "insumer-trust-pq1",
            },
            {"error": {"wallet": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D", "message": "rpc_failure"}},
        ],
        "summary": {"requested": 2, "succeeded": 1, "failed": 1},
    },
    "meta": {"creditsCharged": 3, "creditsRemaining": 997},
}


class TestBatchTrustSummary:
    @patch("langchain_insumer.wrapper.requests.post")
    def test_tool_call_gives_summary_content_and_signed_artifact(self, mock_post, api, mock_response):
        mock_response.json.return_value = BATCH
        mock_post.return_value = mock_response
        tool = InsumerBatchWalletTrustTool(api_wrapper=api)
        msg = tool.invoke({"type": "tool_call", "id": "1", "name": tool.name,
                           "args": {"wallets": [{"wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}]}})
        assert msg.artifact == BATCH
        assert msg.content.startswith("Batch trust profiles: 2 requested, 1 signed, 1 not signed. Credits charged: 3.")
        assert "1. 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 · TRST-AAAAA · check set 2026-10" in msg.content
        assert "signed (insumer-trust-v2 + insumer-trust-pq1)" in msg.content
        assert "stablecoins: 1 of 2 held: USDC on Ethereum" in msg.content
        assert "USDT on Ethereum" not in msg.content
        assert "institutional_stablecoins: 0 of 1 held (1 not evaluated)" in msg.content
        assert "not signed: rpc_failure" in msg.content and "never read this entry as a no" in msg.content
        assert "No credits were charged for it." in msg.content
        assert "c2ln" not in msg.content
        assert "detail" not in mock_post.call_args.kwargs["json"]

    @patch("langchain_insumer.wrapper.requests.post")
    def test_plain_invoke_returns_summary(self, mock_post, api, mock_response):
        mock_response.json.return_value = BATCH
        mock_post.return_value = mock_response
        out = InsumerBatchWalletTrustTool(api_wrapper=api).invoke({"wallets": [{"wallet": "0x" + "ab" * 20}]})
        assert isinstance(out, str) and out.startswith("Batch trust profiles:")

    @patch("langchain_insumer.wrapper.requests.post")
    def test_detail_full_returns_complete_json(self, mock_post, api, mock_response):
        mock_response.json.return_value = BATCH
        mock_post.return_value = mock_response
        out = InsumerBatchWalletTrustTool(api_wrapper=api).invoke({"wallets": [{"wallet": "0x" + "ab" * 20}], "detail": "full"})
        assert json.loads(out) == BATCH
        assert "detail" not in mock_post.call_args.kwargs["json"]

    def test_paid_per_call_wording(self):
        from langchain_insumer.tools._batch_summary import summarize_batch_trust
        text = summarize_batch_trust({**BATCH, "meta": {"creditsCharged": 0, "creditsRemaining": None}})
        assert "Paid per call: the payment covered every wallet requested." in text
        assert "Credits charged" not in text and "No credits were charged" not in text

    def test_unsigned_profile_is_never_shown_as_signed(self):
        from langchain_insumer.tools._batch_summary import summarize_batch_trust
        entry = {"trust": BATCH["data"]["results"][0]["trust"]}
        text = summarize_batch_trust({"ok": True, "data": {"results": [entry]}, "meta": {}})
        assert "returned without a signature: do not rely on it" in text and "signed (" not in text

    def test_malformed_input(self):
        from langchain_insumer.tools._batch_summary import summarize_batch_trust
        assert summarize_batch_trust({"ok": True}) is None
        assert summarize_batch_trust({"ok": True, "data": {"results": "x"}}) is None
        assert summarize_batch_trust("x") is None
        summarize_batch_trust({"ok": True, "data": {"results": [None, "x", 1, {"trust": None}, {"error": "boom"}, {"trust": {"dimensions": "x"}}]}})



def test_signed_count_and_pq_label_need_the_signature_fields():
    from langchain_insumer.tools._batch_summary import summarize_batch_trust
    trust = BATCH["data"]["results"][0]["trust"]
    text = summarize_batch_trust({"ok": True, "data": {"results": [{"trust": trust}, {"trust": trust, "sig": "s", "kid": "k", "pqKid": "p"}]}, "meta": {}})
    assert text.startswith("Batch trust profiles: 2 requested, 1 signed, 1 not signed.")
    assert "signed (k)" in text and "+ p" not in text
