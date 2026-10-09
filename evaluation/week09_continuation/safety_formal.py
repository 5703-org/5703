"""Frozen, bounded HTTP authorization study on an isolated installed release.

This runner records access control and normal-task completion. It does not
score model-mediated prompt injection, hostile upload processing or DoS safety.
Account secrets, bearer tokens and response bodies are never written to disk.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import secrets
from uuid import uuid4

from dotenv import dotenv_values
import httpx


ROOT = Path(__file__).resolve().parents[2]
RELEASE = (
    ROOT.parent
    / "deliverables/CS30-1_Week09_Continuation_v11_20260930/CS30-1_Week09_Continuation_Complete_Project_20260930.zip"
)
CATALOG = (
    ROOT / "evidence/week09-continuation/20260930/visual-full-attempt2/biology-2e-regions.jsonl.gz"
)
SCHEMA = "week09_safety_fixed_authorization_v1"
EXPECTED_RELEASE_SHA256 = "938f59ae246c3e9dd102603417664aaa97a56244a31ea86ea7ea0b7c34737fcb"
SURFACES = (
    "owner_session_detail",
    "owner_session_messages",
    "owner_session_learning_tasks",
    "owner_session_memory_notices",
    "owner_goal_detail",
    "owner_goal_notes",
    "admin_visual_detail",
    "admin_visual_original_page",
    "admin_visual_page_list",
    "admin_users_list",
)
SPLITS = {
    "owner_session_detail": "development",
    "admin_visual_detail": "development",
    "owner_goal_detail": "pilot",
    "admin_users_list": "pilot",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def cases() -> list[dict]:
    result = []
    for surface in SURFACES:
        for index in range(25):
            for attacker in ("other_student", "anonymous"):
                result.append(
                    {
                        "id": f"SEC-{len(result) + 1:03d}",
                        "surface": surface,
                        "index": index,
                        "attacker": attacker,
                        "split": SPLITS.get(surface, "reserved"),
                        "split_group": surface,
                        "expected_legitimate_http": 200,
                        "expected_attack_http": 403
                        if surface.startswith("admin_") and attacker == "other_student"
                        else 401
                        if attacker == "anonymous"
                        else 404,
                    }
                )
    return result


def freeze(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Frozen attack case directory already exists: {output}")
    digest = sha256(RELEASE)
    if digest != EXPECTED_RELEASE_SHA256:
        raise ValueError("The immutable installed-release archive identity changed")
    manifest = {
        "schema": SCHEMA + "_freeze",
        "defense_archive_sha256": digest,
        "evaluator_source_sha256": sha256(Path(__file__)),
        "cases": cases(),
        "unique_attack_surface_groups": len(SURFACES),
        "attack_scope": "Object-level cross-owner reads and administrator read permissions only",
        "attack_content": "No generative prompt, uploaded file or persistent source mutation",
        "split_policy": "Disjoint HTTP attack surfaces: two development, two pilot, six reserved groups",
        "normal_task_pairing": "The owning student or administrator repeats the same GET before each unauthorized GET",
        "semantic_prompt_injection_labels": 0,
    }
    output.mkdir(parents=True)
    (output / "freeze.json").write_bytes(canonical(manifest))
    return {
        "cases": len(manifest["cases"]),
        "groups": len(SURFACES),
        "splits": dict(Counter(row["split"] for row in manifest["cases"])),
        "freeze_sha256": sha256(output / "freeze.json"),
    }


def _call(client: httpx.Client, method: str, path: str, *, json_body=None) -> httpx.Response:
    return client.request(method, path, json=json_body, timeout=30)


def _required(response: httpx.Response, expected: int, action: str) -> dict:
    if response.status_code != expected:
        raise RuntimeError(f"{action}: HTTP {response.status_code}, expected {expected}")
    payload = response.json()
    if "data" not in payload:
        raise RuntimeError(f"{action}: response lacks data envelope")
    return payload["data"]


def _login(client: httpx.Client, email: str, password: str) -> None:
    result = _required(
        _call(client, "POST", "/auth/login", json_body={"email": email, "password": password}),
        200,
        "login",
    )
    client.headers["Authorization"] = "Bearer " + result["access_token"]


def _source_locator(admin: httpx.Client) -> tuple[dict, dict, dict]:
    books = _required(_call(admin, "GET", "/learning/library"), 200, "library")
    biology = next(book for book in books if book["title"] == "Biology 2e")
    sections = _required(
        _call(admin, "GET", f"/learning/library/{biology['id']}/sections?query=Photosynthesis"),
        200,
        "sections",
    )
    section = next(section for section in sections if "Photosynthesis" in section["title"])
    reading = _required(
        _call(
            admin,
            "GET",
            f"/learning/library/{biology['id']}/units?section_id={section['id']}&limit=1",
        ),
        200,
        "reading",
    )
    return biology, section, reading["items"][0]["locator"]


def _visual_samples() -> list[dict]:
    selected = []
    seen_pages = set()
    with gzip.open(CATALOG, "rt", encoding="utf-8") as stream:
        for line in stream:
            region = json.loads(line)
            if region["physical_pdf_page"] in seen_pages:
                continue
            selected.append(region)
            seen_pages.add(region["physical_pdf_page"])
            if len(selected) == 25:
                break
    if len(selected) != 25:
        raise ValueError("The official Biology visual catalog has too few distinct pages")
    return selected


def _prepare_assets(admin: httpx.Client, owner: httpx.Client) -> dict:
    biology, section, locator = _source_locator(admin)
    visuals = _visual_samples()
    assets = {"owner": [], "biology_document_id": biology["id"], "visuals": visuals}
    for index in range(25):
        marker = "ISOLATED_SEC_PRIVATE_" + uuid4().hex
        session = _required(
            _call(owner, "POST", "/sessions", json_body={"title": marker}), 200, "owner session"
        )
        goal = _required(
            _call(
                owner,
                "POST",
                "/learning/goals",
                json_body={
                    "title": marker,
                    "document_id": biology["id"],
                    "section_ids": [section["id"]],
                    "depth": "intermediate",
                },
            ),
            201,
            "owner goal",
        )
        note = _required(
            _call(
                owner,
                "POST",
                "/learning/notes",
                json_body={
                    "title": marker,
                    "content": "Private study note " + marker,
                    "kind": "bookmark",
                    "source": locator,
                    "goal_id": goal["id"],
                    "concepts": ["photosynthesis"],
                },
            ),
            201,
            "owner note",
        )
        assets["owner"].append(
            {
                "session_id": session["id"],
                "goal_id": goal["id"],
                "note_id": note["id"],
                "marker": marker,
            }
        )
    return assets


def _path(case: dict, assets: dict) -> tuple[str, str, str | None]:
    surface = case["surface"]
    index = case["index"]
    owner = assets["owner"][index]
    session_id = owner["session_id"]
    goal_id = owner["goal_id"]
    if surface == "owner_session_detail":
        return f"/sessions/{session_id}", "owner", owner["marker"]
    if surface == "owner_session_messages":
        return f"/sessions/{session_id}/messages", "owner", None
    if surface == "owner_session_learning_tasks":
        return f"/sessions/{session_id}/learning-tasks", "owner", None
    if surface == "owner_session_memory_notices":
        return f"/sessions/{session_id}/memory-notices", "owner", None
    if surface == "owner_goal_detail":
        return f"/learning/goals/{goal_id}", "owner", owner["marker"]
    if surface == "owner_goal_notes":
        return f"/learning/notes?goal_id={goal_id}", "owner", owner["note_id"]
    region = assets["visuals"][index]
    if surface == "admin_visual_detail":
        return (
            f"/admin/source-quality/visual-regions/{region['region_id']}",
            "admin",
            region["region_id"],
        )
    if surface == "admin_visual_original_page":
        return (
            f"/admin/source-quality/visual-regions/{region['region_id']}/original-page",
            "admin",
            None,
        )
    if surface == "admin_visual_page_list":
        return (
            f"/admin/source-quality/visual-regions?document_id={assets['biology_document_id']}&page={region['physical_pdf_page']}",
            "admin",
            None,
        )
    if surface == "admin_users_list":
        return "/admin/users", "admin", None
    raise ValueError(f"Unknown frozen attack surface: {surface}")


def _normal_complete(response: httpx.Response, marker: str | None) -> bool:
    if response.status_code != 200:
        return False
    if response.headers.get("content-type", "").startswith("image/png"):
        return response.content[:8] == b"\x89PNG\r\n\x1a\n"
    if marker:
        return marker in response.text
    return "data" in response.json()


def _security_headers(response: httpx.Response) -> bool:
    return (
        response.headers.get("Cache-Control") == "no-store"
        and response.headers.get("X-Content-Type-Options") == "nosniff"
        and "default-src 'none'" in response.headers.get("Content-Security-Policy", "")
    )


def _summarize(rows: list[dict], frozen: dict, *, setup_account_count: int) -> dict:
    by_surface: dict[str, dict] = {}
    for surface in SURFACES:
        chosen = [row for row in rows if row["surface"] == surface]
        by_surface[surface] = {
            "scheduled": sum(case["surface"] == surface for case in frozen["cases"]),
            "executed": len(chosen),
            "attack_success": sum(row["attack_success"] for row in chosen),
            "safe_legitimate_task_completed": sum(
                row["safe_legitimate_task_completed"] for row in chosen
            ),
            "unexpected_http": sum(not row["expected_attack_http_observed"] for row in chosen),
            "security_headers_present": sum(row["attack_security_headers"] for row in chosen),
        }
    return {
        "schema": SCHEMA + "_public_result",
        "defense_archive_sha256": frozen["defense_archive_sha256"],
        "freeze_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
        "scheduled": len(frozen["cases"]),
        "executed": len(rows),
        "unique_attack_surface_groups": len(SURFACES),
        "attack_success": sum(row["attack_success"] for row in rows),
        "safe_legitimate_task_completed": sum(
            row["safe_legitimate_task_completed"] for row in rows
        ),
        "unexpected_http": sum(not row["expected_attack_http_observed"] for row in rows),
        "security_headers_present": sum(row["attack_security_headers"] for row in rows),
        "by_surface": by_surface,
        "by_split": {
            split: {
                "scheduled": sum(case["split"] == split for case in frozen["cases"]),
                "executed": sum(row["split"] == split for row in rows),
                "attack_success": sum(
                    row["attack_success"] for row in rows if row["split"] == split
                ),
                "safe_legitimate_task_completed": sum(
                    row["safe_legitimate_task_completed"] for row in rows if row["split"] == split
                ),
            }
            for split in ("development", "pilot", "reserved")
        },
        "isolated_student_accounts_created": setup_account_count,
        "model_mode": "mock",
        "provider_calls": 0,
        "provider_cost_usd": 0,
        "human_ratings": 0,
        "model_injection_cases_evaluated": 0,
        "adaptive_attempts_evaluated": 0,
        "scope": "Fixed object authorization GET probes paired with a legitimate GET on the same isolated V11 API. Repeated calls are not independent users or concepts. Other user-requested attack categories remain separate.",
    }


def run(frozen_dir: Path, private_out: Path, stage_root: Path, api_port: int) -> dict:
    if private_out.exists():
        raise FileExistsError("Security run already has an outcome; never replay stateful setup")
    frozen_path = frozen_dir / "freeze.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen["schema"] != SCHEMA + "_freeze" or frozen["cases"] != cases():
        raise ValueError("Frozen security schedule changed")
    if frozen["evaluator_source_sha256"] != sha256(Path(__file__)) or frozen[
        "defense_archive_sha256"
    ] != sha256(RELEASE):
        raise ValueError("Frozen evaluator or defender changed")
    env = dotenv_values(stage_root / ".env")
    if env.get("MODEL_MODE") != "mock":
        raise ValueError(
            "This fixed access-control run is restricted to the isolated mock-model stage"
        )
    admin_password = (
        (stage_root / ".secrets/initial-admin-password.txt").read_text(encoding="utf-8").strip()
    )
    private_out.mkdir(parents=True)
    base = f"http://127.0.0.1:{api_port}/api/v1"
    rows = []
    created = []
    with (
        httpx.Client(base_url=base, timeout=30) as admin,
        httpx.Client(base_url=base, timeout=30) as owner,
        httpx.Client(base_url=base, timeout=30) as other,
        httpx.Client(base_url=base, timeout=30) as anonymous,
    ):
        _login(admin, "admin@example.com", admin_password)
        for client, label in ((owner, "Owner"), (other, "Other")):
            email = "isolated-safety-" + uuid4().hex[:12] + "@example.com"
            password = secrets.token_urlsafe(24)
            account = _required(
                _call(
                    admin,
                    "POST",
                    "/admin/users",
                    json_body={
                        "email": email,
                        "full_name": f"Isolated Security {label}",
                        "password": password,
                        "role": "student",
                    },
                ),
                201,
                "study account",
            )
            created.append({"id": account["id"], "version": account["version"]})
            _login(client, email, password)
        assets = _prepare_assets(admin, owner)
        setup = {
            "freeze_sha256": sha256(frozen_path),
            "defense_archive_sha256": frozen["defense_archive_sha256"],
            "accounts_created": len(created),
            "owner_resource_sets_created": len(assets["owner"]),
            "official_visual_region_count_used": len(assets["visuals"]),
        }
        (private_out / "setup.json").write_bytes(canonical(setup))
        order = {"development": 0, "pilot": 1, "reserved": 2}
        with (private_out / "attempts.jsonl").open("x", encoding="utf-8") as stream:
            for case in sorted(
                frozen["cases"], key=lambda item: (order[item["split"]], item["id"])
            ):
                path, normal_role, marker = _path(case, assets)
                normal = _call(owner if normal_role == "owner" else admin, "GET", path)
                attack = _call(
                    other if case["attacker"] == "other_student" else anonymous, "GET", path
                )
                row = {
                    "id": case["id"],
                    "surface": case["surface"],
                    "split": case["split"],
                    "attacker": case["attacker"],
                    "normal_http": normal.status_code,
                    "attack_http": attack.status_code,
                    "normal_body_sha256": hashlib.sha256(normal.content).hexdigest(),
                    "attack_body_sha256": hashlib.sha256(attack.content).hexdigest(),
                    "attack_success": 200 <= attack.status_code < 300,
                    "safe_legitimate_task_completed": _normal_complete(normal, marker),
                    "expected_attack_http_observed": attack.status_code
                    == case["expected_attack_http"],
                    "attack_security_headers": _security_headers(attack),
                    "private_marker_in_attack_body": bool(marker and marker in attack.text),
                }
                stream.write(canonical(row).decode())
                stream.flush()
                rows.append(row)
        stale_token_checks = []
        for account, client in zip(created, (owner, other)):
            changed = _required(
                _call(
                    admin,
                    "PATCH",
                    f"/admin/users/{account['id']}",
                    json_body={
                        "version": account["version"],
                        "status": "deactivated",
                    },
                ),
                200,
                "deactivate study account",
            )
            stale = _call(client, "GET", "/users/me")
            stale_token_checks.append(
                {
                    "deactivated": changed["status"] == "deactivated",
                    "stale_token_http": stale.status_code,
                }
            )
        (private_out / "stale-token-checks.json").write_bytes(canonical(stale_token_checks))
    summary = _summarize(rows, frozen, setup_account_count=len(created))
    summary["private_marker_leaks"] = sum(row["private_marker_in_attack_body"] for row in rows)
    summary["deactivated_account_old_tokens_blocked"] = sum(
        row["stale_token_http"] in {401, 403} for row in stale_token_checks
    )
    (private_out / "public-summary.json").write_bytes(canonical(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    actions = parser.add_subparsers(dest="action", required=True)
    freeze_parser = actions.add_parser("freeze")
    freeze_parser.add_argument("--out", type=Path, required=True)
    run_parser = actions.add_parser("run")
    run_parser.add_argument("--freeze", type=Path, required=True)
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument("--stage-root", type=Path, required=True)
    run_parser.add_argument("--api-port", type=int, default=18847)
    args = parser.parse_args()
    result = (
        freeze(args.out.resolve())
        if args.action == "freeze"
        else run(
            args.freeze.resolve(), args.out.resolve(), args.stage_root.resolve(), args.api_port
        )
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
