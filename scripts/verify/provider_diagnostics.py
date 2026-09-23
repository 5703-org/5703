"""Explicit bounded provider diagnosis using a managed credential in memory only.

Default invocation prepares a public immutable plan and makes no provider call.
--execute consumes that plan once; started attempts are never replayed.
"""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from sqlalchemy import create_engine, text
from app.core.config import Settings
from app.modules.model_settings.secrets import decrypt
from generation.adapters import test_connection
from generation.capabilities import VERSION, defaults
from generation import probes
from generation.provider_diagnostics import safe_usage
from generation.types import ModelConfig


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--network-label", default="local_operator_reported")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 5})
    with engine.connect() as db:
        row = (
            db.execute(
                text(
                    "SELECT public_config,config_hash,credential_id FROM model_configurations WHERE id=:id"
                ),
                {"id": args.configuration_id},
            )
            .mappings()
            .one()
        )
    source = ModelConfig.from_dict(
        {**row["public_config"], "configuration_id": "model-settings:" + args.configuration_id}
    )
    if (
        source.provider != "openai"
        or source.model != "gpt-5.6-luna"
        or source.base_url.rstrip("/") != "https://api.openai.com/v1"
    ):
        raise SystemExit(
            "This bounded plan is restricted to the reviewed saved OpenAI Luna configuration."
        )
    candidate = replace(
        source,
        max_tokens=2048,
        temperature=None,
        token_limit_parameter="max_completion_tokens",
        reasoning_effort="low",
        capability_version=VERSION,
        capabilities=defaults(source.provider, source.model, source.base_url),
    )
    stages = [
        {
            "id": "00-legacy",
            "tier": "legacy",
            "role": "answer",
            "reserved_output_tokens": 128,
            "max_seconds": 60,
        }
    ]
    prepared = {}
    for role in ("answer", "checker"):
        for tier in ("basic", "structured", "project"):
            name = f"{len(stages):02}-{role}-{tier}"
            prepared[name] = probes.description(candidate, tier, role)
            stages.append({"id": name, **prepared[name]["metadata"], "max_seconds": 60})
    total_output = sum(item["reserved_output_tokens"] for item in stages)
    total_input = sum(item.get("input_tokens", 1000) for item in stages)
    if len(stages) != 7 or total_output > 32768 or total_input > 100000:
        raise SystemExit("Probe plan exceeds its authorized envelope")
    plan = {
        "version": "saved_openai_diagnostic_v1",
        "source_files": {
            name: __import__("hashlib").sha256(Path(name).read_bytes()).hexdigest()
            for name in (
                "scripts/verify/provider_diagnostics.py",
                "generation/probes.py",
                "generation/types.py",
                "generation/providers.py",
                "generation/adapters.py",
                "generation/capabilities.py",
                "generation/provider_diagnostics.py",
                "generation/reliability.py",
                "contracts/models.py",
            )
        },
        "configuration_id": source.configuration_id,
        "saved_config_hash": row["config_hash"],
        "candidate_config": candidate.to_dict(),
        "candidate_hash": probes.digest(candidate.to_dict()),
        "network_label": args.network_label,
        "network_location_verified": False,
        "max_calls": 7,
        "max_active_seconds": 420,
        "reserved_input_tokens": total_input,
        "reserved_output_tokens": total_output,
        "stages": stages,
        "activation": "never",
        "credential_storage": "existing managed reference only; no export",
        "raw_response_storage": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    plan_path = args.output / "plan.json"
    if not args.execute:
        if plan_path.exists() and json.loads(plan_path.read_text(encoding="utf-8")) != plan:
            raise SystemExit("An existing different plan is preserved; use a new directory")
        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "prepared",
                    "plan": str(plan_path),
                    "max_calls": 7,
                    "reserved_input_tokens": total_input,
                    "reserved_output_tokens": total_output,
                    "provider_calls": 0,
                }
            )
        )
        return
    if not plan_path.exists() or json.loads(plan_path.read_text(encoding="utf-8")) != plan:
        raise SystemExit("Prepare and review the exact current plan before execution")
    if any(args.output.glob("attempt-*.json")):
        raise SystemExit("An attempted run exists; uncertain/completed attempts cannot be replayed")
    with engine.connect() as db:
        ciphertext = db.execute(
            text("SELECT ciphertext FROM model_credentials WHERE id=:id"),
            {"id": row["credential_id"]},
        ).scalar_one()
        secret = decrypt(settings, ciphertext)
    blocked_roles = set()
    started = time.monotonic()
    for stage in stages:
        path = args.output / ("attempt-" + stage["id"] + ".json")
        record = {
            "plan_hash": probes.digest(plan),
            "stage_id": stage["id"],
            "tier": stage["tier"],
            "role": stage["role"],
            "started_at": now(),
            "status": "started",
            "configuration_id": source.configuration_id,
        }
        if stage["tier"] != "legacy" and stage["role"] in blocked_roles:
            record.update(status="not_run", reason="Earlier role stage failed", completed_at=now())
        elif time.monotonic() - started >= 420:
            record.update(
                status="not_run", reason="Total active time exhausted", completed_at=now()
            )
        else:
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            result = (
                probes.bounded_call(
                    lambda: test_connection(source, api_key=secret),
                    source,
                    min(60, 420 - (time.monotonic() - started)),
                )
                if stage["tier"] == "legacy"
                else probes.run(
                    prepared[stage["id"]],
                    api_key=secret,
                    timeout_seconds=min(60, 420 - (time.monotonic() - started)),
                )
            )
            record.update(
                status="uncertain"
                if result.error and result.error.get("details", {}).get("uncertain")
                else "failed"
                if result.error
                else "passed",
                completed_at=now(),
                diagnostic=result.diagnostic,
                error_code=result.error.get("code") if result.error else None,
                usage=safe_usage(result.usage),
                latency_ms=result.latency_ms,
                request_submitted=result.request_submitted,
            )
            if result.error and stage["tier"] != "legacy":
                blocked_roles.add(stage["role"])
            if record["status"] == "uncertain":
                blocked_roles.update(("answer", "checker"))
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "stage": stage["id"],
                    "status": record["status"],
                    "error_code": record.get("error_code"),
                }
            )
        )
    secret = None


if __name__ == "__main__":
    main()
