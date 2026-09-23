"""Build an explicitly authored corpus through the real API and durable worker."""

import json
import argparse
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--output", default=str(ROOT / "evidence/integration/demo_corpus.json"))
    args = parser.parse_args()
    client = httpx.Client(base_url=args.base_url, timeout=30)
    login = client.post("/auth/login", json={"email": "admin@example.com", "password": "Passw0rd!"})
    login.raise_for_status()
    client.headers["Authorization"] = "Bearer " + login.json()["data"]["access_token"]

    def call(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if not response.is_success:
            raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
        return response.json()["data"]

    def wait(id):
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            job = call("GET", "/jobs/" + id)
            if job["state"] == "succeeded":
                return job
            if job["state"] in ("failed", "cancelled"):
                raise RuntimeError(json.dumps(job))
            time.sleep(0.3)
        raise RuntimeError("Job observation timed out; check same persisted job before restarting")

    passages = json.loads((ROOT / "evaluation/conversations/source_requirements.json").read_text())[
        "passages"
    ]
    text = "\n\n".join("# " + p["section"] + "\n" + p["text"] for p in passages)
    uploaded = call(
        "POST",
        "/documents",
        data={
            "title": "Authored biology integration notes",
            "edition": "Software fixture v1",
            "license": "Authored for this project; not an OpenStax textbook",
        },
        files={"file": ("authored-biology.txt", text.encode(), "text/plain")},
    )
    print("Uploaded authored source", uploaded["document"]["id"], flush=True)
    processed = call("POST", "/documents/" + uploaded["document"]["id"] + "/process", json={})
    wait(processed["job_id"])
    detail = call("GET", "/documents/" + uploaded["document"]["id"])
    run = next(r for r in detail["processing_runs"] if r["id"] == processed["processing_id"])
    assert run["state"] == "ready", run
    print("Parsed source into", run["counts"], flush=True)
    built = call(
        "POST",
        "/corpus/releases",
        json={"processing_run_ids": [run["id"]], "name": "Authored biology fixture v1"},
    )
    wait(built["job_id"])
    release = call("POST", "/corpus/releases/" + built["release_id"] + "/activate", json={})
    assert release["state"] == "active"
    result = {
        "source_kind": "authored software fixture",
        "document_id": uploaded["document"]["id"],
        "processing_id": run["id"],
        "release_id": release["id"],
        "counts": release["manifest"],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
