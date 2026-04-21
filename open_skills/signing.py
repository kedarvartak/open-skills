from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SIGNATURE_FILE = "OPEN_SKILLS_SIGNATURE.json"
SIGNATURE_ALGORITHM = "hmac-sha256"


class SigningError(ValueError):
    """Raised when package signing or verification fails."""


@dataclass(slots=True)
class PackageSignature:
    signer: str
    algorithm: str
    package_digest: str
    signature: str
    signed_at: str


@dataclass(slots=True)
class SignatureVerification:
    ok: bool
    package_digest: str
    expected_signature: str
    actual_signature: str
    signer: str
    errors: list[str]


def sign_package(skill_root: str | Path, *, signer: str, key: str) -> PackageSignature:
    root = _require_package_root(skill_root)
    package_digest = compute_package_digest(root)
    signature = _sign_digest(package_digest, key)
    payload = {
        "signer": signer,
        "algorithm": SIGNATURE_ALGORITHM,
        "package_digest": package_digest,
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    (root / SIGNATURE_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return PackageSignature(**payload)


def verify_package_signature(skill_root: str | Path, *, key: str) -> SignatureVerification:
    root = _require_package_root(skill_root)
    signature_path = root / SIGNATURE_FILE
    if not signature_path.exists():
        raise SigningError(f"Missing {SIGNATURE_FILE} in {root}")

    payload = json.loads(signature_path.read_text(encoding="utf-8"))
    signer = str(payload.get("signer", ""))
    algorithm = str(payload.get("algorithm", ""))
    actual_digest = compute_package_digest(root)
    stored_digest = str(payload.get("package_digest", ""))
    actual_signature = str(payload.get("signature", ""))
    expected_signature = _sign_digest(actual_digest, key)
    errors: list[str] = []

    if algorithm != SIGNATURE_ALGORITHM:
        errors.append(f"Unsupported signature algorithm: {algorithm}")
    if stored_digest != actual_digest:
        errors.append("Package digest does not match signed digest")
    if not hmac.compare_digest(actual_signature, expected_signature):
        errors.append("Signature does not match package digest and key")

    return SignatureVerification(
        ok=not errors,
        package_digest=actual_digest,
        expected_signature=expected_signature,
        actual_signature=actual_signature,
        signer=signer,
        errors=errors,
    )


def compute_package_digest(skill_root: str | Path) -> str:
    root = _require_package_root(skill_root)
    file_entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if _should_skip(path, root):
            continue
        relative_path = path.relative_to(root).as_posix()
        file_entries.append(
            {
                "path": relative_path,
                "sha256": _hash_file(path),
                "size": path.stat().st_size,
            }
        )

    manifest_bytes = json.dumps(file_entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(manifest_bytes).hexdigest()


def _require_package_root(skill_root: str | Path) -> Path:
    root = Path(skill_root).resolve()
    if not root.exists() or not root.is_dir():
        raise SigningError(f"Skill package directory does not exist: {root}")
    if not (root / "SKILL.md").exists():
        raise SigningError(f"Missing SKILL.md in {root}")
    return root


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sign_digest(package_digest: str, key: str) -> str:
    return hmac.new(key.encode(), package_digest.encode(), hashlib.sha256).hexdigest()


def _should_skip(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if path.name == SIGNATURE_FILE:
        return True
    if "__pycache__" in relative_parts:
        return True
    return path.suffix == ".pyc"
