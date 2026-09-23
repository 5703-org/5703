"""One-time migration from untyped envelopes to documented HTTP payloads."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPINGS = {
    "identity/router.py": (
        {
            "login": "TokenData",
            "read_me": "UserOut",
            "update_me": "UserOut",
            "admin_list_users": "list[UserOut]",
            "read_profile": "Profile",
            "put_profile": "Profile",
            "reset_profile": "Profile",
        },
        "from app.modules.identity.schemas import UserOut\nfrom contracts.models import Profile\n",
    ),
    "identity/accounts.py": (
        {"change_password": "dict[str, bool]", "create_user": "UserOut", "update_user": "UserOut"},
        "from app.modules.identity.schemas import UserOut\n",
    ),
    "learning/router.py": (
        {
            "create_session": "SessionOut",
            "list_sessions": "list[SessionOut]",
            "read_session": "SessionOut",
            "rename_session": "SessionOut",
            "archive_session": "SessionOut",
            "restore_session": "SessionOut",
            "delete_session": "dict",
        },
        "from app.modules.learning.schemas import SessionOut\n",
    ),
    "answering/router.py": (
        {
            "send_message": "JobReceipt",
            "messages": "MessagePage",
            "job": "JobOut",
            "cancel": "JobOut",
            "retry": "JobReceipt",
            "regenerate": "JobReceipt",
            "answer": "AnswerOut",
            "evidence": "EvidenceSnapshot",
            "feedback": "FeedbackOut | None",
            "put_feedback": "FeedbackOut",
            "all_feedback": "list[FeedbackOut]",
            "review": "FeedbackOut",
            "summary": "SummaryOut",
        },
        "from contracts.models import JobReceipt, MessagePage, JobOut, AnswerOut, EvidenceSnapshot\nfrom contracts.http import FeedbackOut, SummaryOut\n",
    ),
    "administration/router.py": (
        {"capabilities": "CapabilitiesOut", "list_events": "list[dict]"},
        "from contracts.http import CapabilitiesOut\n",
    ),
    "knowledge/router.py": (
        {
            "documents": "list[dict]",
            "upload": "dict",
            "document": "dict",
            "process": "dict",
            "deactivate": "dict",
            "restore": "dict",
            "revoke": "dict",
            "releases": "list[dict]",
            "create_release": "dict",
            "activate": "dict",
            "configs": "list[dict]",
            "create_config": "dict",
        },
        "",
    ),
}


def main():
    for name, (mapping, extra) in MAPPINGS.items():
        path = ROOT / "backend/app/modules" / name
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.startswith(("def ", "async def ")):
                function = line.split("def ", 1)[1].split("(", 1)[0]
                if function not in mapping:
                    continue
                cursor = index - 1
                while cursor >= 0 and lines[cursor].startswith("@router."):
                    if "response_model=" not in lines[cursor]:
                        lines[cursor] = (
                            lines[cursor][:-1] + f", response_model=Envelope[{mapping[function]}])"
                        )
                    cursor -= 1
        # Imports must follow any future import and precede normal imports.
        position = next(
            i for i, line in enumerate(lines) if line.startswith(("from fastapi", "from typing"))
        )
        lines.insert(position, "from contracts.http import Envelope\n" + extra.rstrip())
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
