#!/usr/bin/env python3
"""Check portable package structure and accidental private dependencies."""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"qiuzhi-dispatch", "qiuzhi-agent", "qiuzhi-coach", "qiuzhi-course", "qiuzhi-delivery"}
CSV_COLUMNS = "id,date,company,role,resume_version,version_verified,greeting_version,status,stage,next_action,notes".split(",")


def main():
    errors = []
    files = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.is_symlink():
            errors.append(f"Symbolic link is not portable: {relative}")
            continue
        if not path.is_file():
            continue
        if path.suffix == ".pyc":
            continue
        files.append(path)
        if any(part in {"evals", ".qiuzhi", ".env", "private", ".private"} for part in relative.parts):
            errors.append(f"Private runtime file included: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Unexpected binary file: {relative}")
            continue
        for label, pattern in [
            ("local user path", r"/(?:Users|home)/[^/\s]+/"),
            ("private cloud document", r"https?://[^\s/]+\.(?:feishu|larksuite)\.(?:cn|com)/"),
            ("access token", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
            ("private key", r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
            ("personal phone", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
        ]:
            if re.search(pattern, text):
                errors.append(f"Possible {label}: {relative}")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                errors.append(f"Invalid JSON {relative}: {exc}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = target.strip("<>").split("#", 1)[0]
                if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    errors.append(f"Broken or nonportable link in {relative}: {target}")

    found = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    if found != SKILLS:
        errors.append(f"Expected {sorted(SKILLS)}, found {sorted(found)}")
    for name in found:
        path = ROOT / "skills" / name / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\n(.*?)\n---(?:\n|$)", content, re.S)
        if not frontmatter:
            errors.append(f"Missing frontmatter: {name}")
            continue
        if not re.search(rf"^name: {re.escape(name)}$", frontmatter.group(1), re.M):
            errors.append(f"Name mismatch: {name}")
        if not re.search(r"^description:\s*\S", frontmatter.group(1), re.M):
            errors.append(f"Missing description: {name}")

    candidates_path = ROOT / "skills/qiuzhi-dispatch/references/candidates.json"
    if candidates_path.exists():
        try:
            candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["candidates"]
            names = [c["name"] for c in candidates]
            if len(names) != len(set(names)) or set(names) != SKILLS - {"qiuzhi-dispatch"}:
                errors.append("Candidate list does not match installed leaf skills")
        except (KeyError, ValueError, TypeError):
            errors.append("Invalid candidate list")
    else:
        errors.append("Missing candidate list")

    template = ROOT / "skills/qiuzhi-dispatch/assets/ledger.example.csv"
    if template.exists():
        with template.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if rows != [CSV_COLUMNS]:
            errors.append("Ledger template must contain the exact header and no personal rows")
    else:
        errors.append("Missing ledger template")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(found)} skills, {len(files)} files, relative links and candidate list valid; no flagged private dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
