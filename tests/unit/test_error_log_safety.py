"""Unexpected database errors must not expose bound inputs through log sinks."""

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import StatementError

from app.core.exceptions import register_exception_handlers
from app.core.logging import JsonFormatter


def test_unexpected_database_error_omits_sql_parameters_and_exception_chain(caplog):
    app = FastAPI()
    register_exception_handlers(app)
    password = "private-password-928471"
    question = "private-question-731985"

    @app.get("/failure")
    def fail():
        cause = ValueError("upstream credential " + password)
        raise StatementError(
            "database rejected " + question,
            "INSERT INTO private_table VALUES (:password, :question)",
            {"password": password, "question": question},
            cause,
        ) from cause

    with caplog.at_level(logging.ERROR, logger="app.errors"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    records = [record for record in caplog.records if record.name == "app.errors"]
    assert len(records) == 1
    record = records[0]
    assert record.event == "unhandled_error"
    assert "StatementError" in record.getMessage()
    assert record.exc_info is None and record.exc_text is None
    logged = JsonFormatter().format(record)
    assert json.loads(logged)["event"] == "unhandled_error"
    for secret in (password, question, "INSERT INTO", "private_table", "upstream credential"):
        assert secret not in logged + caplog.text + response.text
