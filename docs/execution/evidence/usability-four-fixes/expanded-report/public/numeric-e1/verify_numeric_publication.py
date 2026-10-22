"""No-database current-source publication controls using authored in-memory rows.

Compile complete production function bodies without importing application database
or runtime modules. Repository lookup, row locking/flush and released membership
are explicit authored seams. This is not PostgreSQL, HTTP, concurrency, source
semantic correctness or live provider acceptance.
"""

import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path("E:/5703/learning-assistant").resolve()
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))


def fence(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "sqlite3.connect", "subprocess.Popen",
                 "os.system", "os.startfile", "os.posix_spawn", "os.fork"}:
        raise RuntimeError("OFFLINE_FIXTURE_FORBIDS_NETWORK_DATABASE_AND_CHILD_PROCESSES")
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve()
        if ".secrets" in {part.lower() for part in path.parts} or path.name.lower() == ".env" or path.name.lower().startswith(".env."):
            raise RuntimeError("OFFLINE_FIXTURE_FORBIDS_CREDENTIAL_READS")
        mode = args[1] or ""
        flags = args[2] or 0
        writing = any(flag in mode for flag in "wax+") or flags & (1 | 2 | 64 | 512 | 1024)
        if writing and not path.is_relative_to(HERE):
            raise RuntimeError("OFFLINE_FIXTURE_FORBIDS_WRITES_OUTSIDE_OWN_SCRATCH")


sys.addaudithook(fence)

from contracts.study import PracticeRubric, PublishInput, PracticeResponse  # noqa: E402


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def import_pure(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


grading = import_pure("numeric_fixture_grading", ROOT / "backend/app/modules/learning_product/grading.py")
exception_source = ROOT / "backend/app/core/exceptions.py"
exception_tree = ast.parse(exception_source.read_text(encoding="utf-8"), str(exception_source))
exception_class = [node for node in exception_tree.body if isinstance(node, ast.ClassDef) and node.name == "AppError"]
assert len(exception_class) == 1
exception_namespace = {}
exec(compile(ast.Module(body=exception_class, type_ignores=[]), str(exception_source), "exec"), exception_namespace)
AppError = exception_namespace["AppError"]


def production_functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == set(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


class Column:
    def __init__(self, name):
        self.name = name

    def __eq__(self, expected):
        return self.name, expected


class AuthoredItem(SimpleNamespace):
    id = Column("id")
    workspace_id = Column("workspace_id")


class AuthoredSelect:
    def __init__(self, model):
        assert model is AuthoredItem
        self.conditions = None

    def where(self, *conditions):
        assert {condition[0] for condition in conditions} == {"id", "workspace_id"}
        self.conditions = conditions
        return self


class AuthoredRepository:
    """An explicit lookup/lock/flush seam; no database session or engine exists."""

    def __init__(self, item):
        self.item = item
        self.lock_reads = 0
        self.flushes = 0

    def scalar(self, query):
        assert isinstance(query, AuthoredSelect) and query.conditions is not None
        return self.item if all(getattr(self.item, key) == value for key, value in query.conditions) else None

    def refresh(self, item, *, with_for_update):
        assert item is self.item and with_for_update is True
        self.lock_reads += 1

    def flush(self):
        self.flushes += 1


def authored_membership(db, actor, document_id, release_id):
    assert isinstance(db, AuthoredRepository)
    if actor.workspace_id != "authored-workspace" or (document_id, release_id) != ("authored-document", "authored-release"):
        raise AppError("EVIDENCE_UNAVAILABLE")
    return SimpleNamespace(id=release_id), [], [db.unit]


library_namespace = {"hashlib": hashlib, "json": json, "AppError": AppError,
                     "book_data": authored_membership}
library = production_functions(
    ROOT / "backend/app/modules/learning_product/library.py",
    {"text_hash", "section_id", "validate_locator"}, library_namespace,
)
service = production_functions(
    ROOT / "backend/app/modules/learning_product/service.py",
    {"stamp", "cas", "practice_item", "item_out", "admin_out", "validate_item", "publish_item"},
    {"select": AuthoredSelect, "PracticeItem": AuthoredItem, "AppError": AppError,
     "library": library, "grading": grading,
     "utcnow": lambda: datetime(2026, 10, 19, tzinfo=timezone.utc)},
)


def authored_fixture(unit="mol"):
    source_text = f"The authored beaker contains 2 {unit} of solute. State the amount in {unit}."
    actor = SimpleNamespace(id="authored-administrator", workspace_id="authored-workspace")
    source = {"document_id": "authored-document", "release_id": "authored-release",
              "processing_id": "authored-processing", "source_unit_id": "authored-source-unit",
              "text_hash": library.text_hash(source_text), "start": 0, "end": len(source_text)}
    rubric = PracticeRubric(numeric={"value": 2.0, "unit": unit}, explanation=f"The source directly states 2 {unit}.")
    item = AuthoredItem(id="authored-item", workspace_id=actor.workspace_id, creator_id=actor.id,
                       state="draft", version=1, item_revision=1,
                       public_payload={"kind": "numeric", "title": "Authored amount", "prompt": source_text, "options": []},
                       private_rubric=rubric.model_dump(), source=source, validation={"status": "pending"})
    db = AuthoredRepository(item)
    db.unit = SimpleNamespace(id="authored-source-unit", processing_id="authored-processing",
                              section="Authored quantities", cleaned_text=source_text)
    return db, actor, item


OBSERVATIONS = []


class NumericPublicationControls(unittest.TestCase):
    def test_supported_mol_validate_returned_revision_publishes(self):
        db, actor, item = authored_fixture()
        checked = service.validate_item(db, actor, item.id)
        self.assertEqual((checked["state"], checked["version"], checked["validation_details"]["status"]), ("validated", 2, "passed"))
        self.assertEqual(checked["validation_details"]["issues"], [])
        self.assertIsNone(checked["validation_details"]["semantic_correctness_verified"])
        published = service.publish_item(db, actor, item.id,
            PublishInput(expected_version=checked["version"], confirm_source_and_solvability=True))
        self.assertEqual((published["state"], published["version"]), ("published", 3))
        self.assertTrue(published["validation_details"]["publisher_confirmed"])
        result = grading.grade("numeric", PracticeResponse(value=2.0, unit="mol"), item.private_rubric)
        self.assertEqual(result["outcome"], "correct")
        OBSERVATIONS.append({"case": "supported_mol", "validation_version": 2, "publication_version": 3,
                             "status": "passed", "published": True, "authored_correct_response": result["outcome"]})

    def test_revalidation_advances_version_and_stale_publication_conflicts(self):
        db, actor, item = authored_fixture()
        first = service.validate_item(db, actor, item.id)
        second = service.validate_item(db, actor, item.id)
        self.assertEqual((first["version"], second["version"]), (2, 3))
        before = deepcopy(vars(item))
        with self.assertRaises(AppError) as caught:
            service.publish_item(db, actor, item.id, PublishInput(expected_version=first["version"], confirm_source_and_solvability=True))
        self.assertEqual(caught.exception.code, "CONFLICT")
        self.assertEqual(vars(item), before)
        published = service.publish_item(db, actor, item.id, PublishInput(expected_version=second["version"], confirm_source_and_solvability=True))
        self.assertEqual((published["state"], published["version"]), ("published", 4))
        OBSERVATIONS.append({"case": "repeat_validate", "versions": [2, 3, 4], "stale_version_conflict_preserves_item": True})

    def test_unsupported_mmol_remains_draft_and_cannot_publish_at_returned_version(self):
        db, actor, item = authored_fixture("mmol")
        checked = service.validate_item(db, actor, item.id)
        self.assertEqual((checked["version"], checked["state"], checked["validation_details"]["status"]), (2, "draft", "failed"))
        self.assertEqual(checked["validation_details"]["issues"], ["missing_or_unsupported_numeric_key"])
        before = deepcopy(vars(item))
        with self.assertRaises(AppError) as caught:
            service.publish_item(db, actor, item.id, PublishInput(expected_version=checked["version"], confirm_source_and_solvability=True))
        self.assertEqual(caught.exception.code, "CONFLICT")
        self.assertEqual(vars(item), before)
        OBSERVATIONS.append({"case": "unsupported_mmol", "validation_version": 2, "status": "failed",
                             "issues": checked["validation_details"]["issues"], "publish_conflict": True})

    def test_unvalidated_and_unconfirmed_publication_remain_denied(self):
        for validate in (False, True):
            with self.subTest(validated=validate):
                db, actor, item = authored_fixture()
                if validate:
                    service.validate_item(db, actor, item.id)
                before = deepcopy(vars(item))
                with self.assertRaises(AppError) as caught:
                    service.publish_item(db, actor, item.id, PublishInput(expected_version=item.version, confirm_source_and_solvability=not validate))
                self.assertEqual(caught.exception.code, "CONFLICT")
                self.assertEqual(vars(item), before)

    def test_source_identity_and_workspace_failures_do_not_validate(self):
        for kind in ("source_hash", "workspace"):
            with self.subTest(kind=kind):
                db, actor, item = authored_fixture()
                if kind == "source_hash":
                    item.source["text_hash"] = "0" * 64
                else:
                    actor.workspace_id = "foreign-workspace"
                before = deepcopy(vars(item))
                with self.assertRaises(AppError) as caught:
                    service.validate_item(db, actor, item.id)
                self.assertEqual(caught.exception.code, "EVIDENCE_UNAVAILABLE" if kind == "source_hash" else "NOT_FOUND")
                self.assertEqual(vars(item), before)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NumericPublicationControls))
    payload = {"schema": "expanded_report_numeric_no_database_controls_v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
               "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "observations": OBSERVATIONS,
               "scope": "Exact production function bodies; authored repository/locking/flush/released-membership seams; no HTTP or database execution",
               "not_proven": ["PostgreSQL atomicity or concurrency", "the tester's omitted private rubric/answers", "source semantic correctness", "live proposal quality"],
               "network_database_provider_native_actions": 0, "Main_writes": 0,
               "source_pins": [pin(ROOT / name) for name in ("backend/app/modules/learning_product/service.py", "backend/app/modules/learning_product/library.py", "backend/app/modules/learning_product/grading.py", "backend/app/core/exceptions.py", "contracts/study.py")],
               "script": pin(Path(__file__))}
    (HERE / "NUMERIC-CONTROLS-RESULT.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
