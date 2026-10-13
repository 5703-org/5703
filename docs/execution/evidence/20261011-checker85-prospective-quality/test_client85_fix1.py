"""Focused message-header protocol controls; no Main imports, auth, DB or network."""

import ast
import hashlib
import io
import json
import socket
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import api_client85_fix1 as client
import test_client85 as fixtures

HERE = Path(__file__).resolve().parent
RUN = (
    HERE
    / "fix1-controls"
    / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
)
ROUTER = Path("E:/5703/learning-assistant/backend/app/modules/answering/router.py")


class HeaderAwareAPI(fixtures.FakeAPI):
    def __init__(self):
        super().__init__()
        self.submission_headers = []
        self.message_status = 202

    def __call__(self, method, path, body, token, timeout, *, idempotency_key=None):
        if method == "POST" and path.endswith("/messages"):
            self.submission_headers.append(idempotency_key)
            if idempotency_key is None or self.message_status != 202:
                self.calls.append((method, path, body, token, timeout))
                return (
                    self.message_status if idempotency_key else 422,
                    b'{"detail":"FAKE_LOCAL_TOKEN private body"}',
                )
        try:
            return super().__call__(method, path, body, token, timeout)
        except fixtures.client.ClientStop as error:
            # The reused fixture raises the original module's exception type.
            raise client.ClientStop(error.code) from None


class ProtocolControls(unittest.TestCase):
    def setUp(self):
        self.runtime = RUN / self.id().split(".")[-1]
        self.case = self.runtime / "case02"
        self.case.mkdir(parents=True)
        self.scope = self.runtime / "scope85-case02.json"
        raw = json.dumps(
            {
                "case_id": "case02",
                "question_id": "Q85_02",
                "question_text": fixtures.QUESTION,
            }
        ).encode()
        self.scope.write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        self.claim = {
            "case_id": "case02",
            "question_id": "Q85_02",
            "question_sha256": hashlib.sha256(fixtures.QUESTION.encode()).hexdigest(),
            "scope_sha256": self.pin,
        }
        (self.case / "api-claim77.json").write_text(
            json.dumps(self.claim), encoding="utf-8"
        )
        self.clock, self.api = fixtures.FakeClock(), HeaderAwareAPI()
        self.login = {
            "email": "fake-fixture@example.invalid",
            "password": "fake_fixture_password",
        }

    def run_client(self):
        with patch.object(
            socket, "socket", side_effect=AssertionError("NETWORK_FORBIDDEN")
        ):
            return client.run_case(
                self.case,
                self.scope,
                self.pin,
                login=self.login,
                transport=self.api,
                clock=self.clock,
                sleep=self.clock.sleep,
                runtime=self.runtime,
            )

    def test_actual_endpoint_requires_header_annotation(self):
        tree = ast.parse(ROUTER.read_bytes())
        endpoint = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "send_message"
        )
        index = next(
            index
            for index, arg in enumerate(endpoint.args.args)
            if arg.arg == "idempotency_key"
        )
        defaults_start = len(endpoint.args.args) - len(endpoint.args.defaults)
        default = endpoint.args.defaults[index - defaults_start]
        self.assertIsInstance(default, ast.Call)
        self.assertIsInstance(default.func, ast.Name)
        self.assertEqual(default.func.id, "Header")
        self.assertEqual(len(default.args), 1)
        self.assertIs(default.args[0].value, Ellipsis)

    def test_normal_case_header_binds_scope_session_and_message_once(self):
        receipt = self.run_client()
        self.assertEqual(receipt["status"], "API_COMPLETED")
        expected = (
            "checker85-"
            + hashlib.sha256(f"case02|{self.pin}|{fixtures.SID}".encode()).hexdigest()
        )
        self.assertEqual(self.api.submission_headers, [expected])
        self.assertLessEqual(len(expected), 128)
        self.assertEqual(
            receipt["message_idempotency_key_sha256"],
            hashlib.sha256(expected.encode()).hexdigest(),
        )
        self.assertEqual(receipt["message_post_attempts"], 1)
        self.assertEqual(receipt["new_message_submissions"], 1)
        self.assertEqual(receipt["automatic_retries"], 0)
        self.assertEqual(receipt["n"], 0)
        self.assertIsNone(receipt["send_to_complete_dom_ms"])
        self.assertNotIn(expected, json.dumps(receipt))

    def test_missing_required_header_negative_control(self):
        status, _ = self.api(
            "POST", f"/api/v1/sessions/{fixtures.SID}/messages", {}, None, 10
        )
        self.assertEqual(status, 422)
        self.assertEqual(self.api.submission_headers, [None])

    def test_urllib_request_contains_real_header_only_on_message(self):
        requests = []

        class FakeResponse:
            status = 202

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, size):
                return b'{"data":{}}'

        class FakeOpener:
            def open(self, request, timeout):
                requests.append(request)
                return FakeResponse()

        transport = client.LocalTransport()
        transport.opener = FakeOpener()
        key = "checker85-" + "a" * 64
        with patch.object(
            socket, "socket", side_effect=AssertionError("NETWORK_FORBIDDEN")
        ):
            status, _ = transport(
                "POST",
                f"/api/v1/sessions/{fixtures.SID}/messages",
                {},
                "FAKE_LOCAL_TOKEN",
                10,
                idempotency_key=key,
            )
            self.assertEqual(status, 202)
            self.assertEqual(requests[0].get_header("Idempotency-key"), key)
            self.assertEqual(
                requests[0].full_url,
                client.ORIGIN + f"/api/v1/sessions/{fixtures.SID}/messages",
            )
            transport("POST", "/api/v1/sessions", {}, "FAKE_LOCAL_TOKEN", 10)
            self.assertIsNone(requests[1].get_header("Idempotency-key"))
            with self.assertRaises(client.ClientStop):
                transport(
                    "POST", "/api/v1/auth/login", {}, None, 10, idempotency_key=key
                )
        self.assertEqual(len(requests), 2)

    def test_numeric_http_failure_diagnostic_no_body_or_retry(self):
        self.api.message_status = 422
        receipt = self.run_client()
        self.assertEqual(receipt["status"], "STOPPED_PRESERVE_NEW_ROWS")
        self.assertEqual(receipt["error"]["code"], "LOCAL_API_HTTP_STATUS")
        self.assertEqual(receipt["failed_http_status"], 422)
        self.assertEqual(receipt["failed_http_method"], "POST")
        self.assertEqual(receipt["new_message_submissions"], 0)
        self.assertEqual(receipt["automatic_retries"], 0)
        self.assertEqual(len(self.api.submission_headers), 1)
        self.assertEqual(receipt["api_close_status"], 200)
        self.assertNotIn("private body", json.dumps(receipt))

    def test_lost_message_response_remains_single_attempt(self):
        self.api.network_error_on_send = True
        receipt = self.run_client()
        self.assertEqual(receipt["message_post_attempts"], 1)
        self.assertEqual(receipt["automatic_retries"], 0)
        self.assertEqual(receipt["error"]["code"], "LOCAL_API_TRANSPORT_FAILED")
        self.assertEqual(len(self.api.submission_headers), 1)
        self.assertEqual(receipt["api_close_status"], 200)


if __name__ == "__main__":
    RUN.mkdir(parents=True)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ProtocolControls)
    )
    (RUN / "test-output.txt").write_text(output.getvalue(), encoding="utf-8")
    receipt = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "network_calls": 0,
        "auth_reads": 0,
        "database_reads": 0,
        "database_writes": 0,
        "Main_runtime_imports": 0,
        "Main_source_read_only": True,
        "provider_posts": 0,
        "synthetic_inputs_only": True,
        "run_directory": str(RUN),
    }
    (RUN / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
