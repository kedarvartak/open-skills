from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from secrets import randbelow, randbits

SIGNATURE_FILE = "OPEN_SKILLS_SIGNATURE.json"
SIGNATURE_ALGORITHM = "rsa-sha256-pkcs1-v1_5"
PUBLIC_KEY_ALGORITHM = "rsa"

_DEFAULT_KEY_BITS = 2048
_PUBLIC_EXPONENT = 65537
_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class SigningError(ValueError):
    """Raised when package signing or verification fails."""


@dataclass(slots=True)
class PackageSignature:
    signer: str
    algorithm: str
    public_key_id: str
    package_digest: str
    signature: str
    signed_at: str
    provenance: dict[str, str]


@dataclass(slots=True)
class SignatureVerification:
    ok: bool
    package_digest: str
    actual_signature: str
    signer: str
    public_key_id: str
    errors: list[str]


def generate_keypair(private_key_path: str | Path, public_key_path: str | Path, *, signer: str) -> str:
    private_key = _generate_rsa_private_key(_DEFAULT_KEY_BITS)
    public_key = _public_key_from_private(private_key)
    public_key.update({"type": "open-skills-public-key", "signer": signer})
    public_key["key_id"] = public_key_id(public_key)

    private_payload = {
        "type": "open-skills-private-key",
        "algorithm": PUBLIC_KEY_ALGORITHM,
        "signer": signer,
        "key_id": public_key["key_id"],
        "n": _int_to_b64(private_key["n"]),
        "e": _int_to_b64(private_key["e"]),
        "d": _int_to_b64(private_key["d"]),
        "p": _int_to_b64(private_key["p"]),
        "q": _int_to_b64(private_key["q"]),
    }

    Path(private_key_path).write_text(json.dumps(private_payload, indent=2) + "\n", encoding="utf-8")
    Path(public_key_path).write_text(json.dumps(public_key, indent=2) + "\n", encoding="utf-8")
    return str(public_key["key_id"])


def sign_package(
    skill_root: str | Path,
    *,
    signer: str,
    private_key_path: str | Path,
    provenance: dict[str, str] | None = None,
) -> PackageSignature:
    root = _require_package_root(skill_root)
    private_key = _load_private_key(private_key_path)
    package_digest = compute_package_digest(root)
    key_id = public_key_id(_public_key_from_private(private_key))
    signature = _sign_digest(package_digest, private_key)
    payload = {
        "signer": signer,
        "algorithm": SIGNATURE_ALGORITHM,
        "public_key_id": key_id,
        "package_digest": package_digest,
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provenance": provenance or {},
    }
    (root / SIGNATURE_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return PackageSignature(**payload)


def verify_package_signature(
    skill_root: str | Path,
    *,
    public_key_path: str | Path,
) -> SignatureVerification:
    root = _require_package_root(skill_root)
    signature_path = root / SIGNATURE_FILE
    if not signature_path.exists():
        raise SigningError(f"Missing {SIGNATURE_FILE} in {root}")

    payload = json.loads(signature_path.read_text(encoding="utf-8"))
    public_key = _load_public_key(public_key_path)
    signer = str(payload.get("signer", ""))
    algorithm = str(payload.get("algorithm", ""))
    signed_key_id = str(payload.get("public_key_id", ""))
    actual_key_id = public_key_id(public_key)
    actual_digest = compute_package_digest(root)
    stored_digest = str(payload.get("package_digest", ""))
    actual_signature = str(payload.get("signature", ""))
    errors: list[str] = []

    if algorithm != SIGNATURE_ALGORITHM:
        errors.append(f"Unsupported signature algorithm: {algorithm}")
    if signed_key_id != actual_key_id:
        errors.append("Signature public key id does not match the provided public key")
    if stored_digest != actual_digest:
        errors.append("Package digest does not match signed digest")
    if not _verify_digest(actual_digest, actual_signature, public_key):
        errors.append("Signature does not match package digest and public key")

    return SignatureVerification(
        ok=not errors,
        package_digest=actual_digest,
        actual_signature=actual_signature,
        signer=signer,
        public_key_id=signed_key_id,
        errors=errors,
    )


def read_signature(skill_root: str | Path) -> PackageSignature | None:
    root = _require_package_root(skill_root)
    signature_path = root / SIGNATURE_FILE
    if not signature_path.exists():
        return None
    payload = json.loads(signature_path.read_text(encoding="utf-8"))
    return PackageSignature(
        signer=str(payload.get("signer", "")),
        algorithm=str(payload.get("algorithm", "")),
        public_key_id=str(payload.get("public_key_id", "")),
        package_digest=str(payload.get("package_digest", "")),
        signature=str(payload.get("signature", "")),
        signed_at=str(payload.get("signed_at", "")),
        provenance=dict(payload.get("provenance", {})),
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


def public_key_id(public_key: dict[str, object]) -> str:
    stable = {
        "algorithm": public_key.get("algorithm"),
        "n": public_key.get("n"),
        "e": public_key.get("e"),
    }
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()[:24]


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


def _should_skip(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if path.name == SIGNATURE_FILE:
        return True
    if "__pycache__" in relative_parts:
        return True
    return path.suffix == ".pyc"


def _load_private_key(path: str | Path) -> dict[str, int]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("type") != "open-skills-private-key":
        raise SigningError("Invalid Open Skills private key file")
    return {
        "n": _b64_to_int(str(payload["n"])),
        "e": _b64_to_int(str(payload["e"])),
        "d": _b64_to_int(str(payload["d"])),
        "p": _b64_to_int(str(payload["p"])),
        "q": _b64_to_int(str(payload["q"])),
    }


def _load_public_key(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("type") != "open-skills-public-key":
        raise SigningError("Invalid Open Skills public key file")
    return {
        "algorithm": str(payload.get("algorithm", PUBLIC_KEY_ALGORITHM)),
        "n": str(payload["n"]),
        "e": str(payload["e"]),
        "n_int": _b64_to_int(str(payload["n"])),
        "e_int": _b64_to_int(str(payload["e"])),
    }


def _public_key_from_private(private_key: dict[str, int]) -> dict[str, object]:
    return {
        "algorithm": PUBLIC_KEY_ALGORITHM,
        "n": _int_to_b64(private_key["n"]),
        "e": _int_to_b64(private_key["e"]),
    }


def _sign_digest(package_digest: str, private_key: dict[str, int]) -> str:
    encoded = _emsa_pkcs1_v1_5_encode(bytes.fromhex(package_digest), _byte_length(private_key["n"]))
    signature_int = pow(int.from_bytes(encoded, "big"), private_key["d"], private_key["n"])
    return _int_to_b64(signature_int, length=_byte_length(private_key["n"]))


def _verify_digest(package_digest: str, signature: str, public_key: dict[str, object]) -> bool:
    try:
        n = int(public_key["n_int"])
        e = int(public_key["e_int"])
        signature_int = _b64_to_int(signature)
        expected = _emsa_pkcs1_v1_5_encode(bytes.fromhex(package_digest), _byte_length(n))
        actual_int = pow(signature_int, e, n)
        actual = actual_int.to_bytes(_byte_length(n), "big")
        return actual == expected
    except (ValueError, OverflowError):
        return False


def _emsa_pkcs1_v1_5_encode(digest: bytes, length: int) -> bytes:
    digest_info = _SHA256_DER_PREFIX + digest
    padding_length = length - len(digest_info) - 3
    if padding_length < 8:
        raise SigningError("RSA key is too small for SHA-256 signatures")
    return b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info


def _generate_rsa_private_key(bits: int) -> dict[str, int]:
    half = bits // 2
    while True:
        p = _generate_prime(half)
        q = _generate_prime(bits - half)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        if _gcd(_PUBLIC_EXPONENT, phi) == 1:
            break
    n = p * q
    d = pow(_PUBLIC_EXPONENT, -1, phi)
    return {"n": n, "e": _PUBLIC_EXPONENT, "d": d, "p": p, "q": q}


def _generate_prime(bits: int) -> int:
    while True:
        candidate = randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


def _is_probable_prime(value: int, rounds: int = 16) -> bool:
    if value < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if value in small_primes:
        return True
    if any(value % prime == 0 for prime in small_primes):
        return False

    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    for _ in range(rounds):
        a = 2 + randbelow(value - 3)
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, value)
            if x == value - 1:
                break
        else:
            return False
    return True


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _byte_length(value: int) -> int:
    return (value.bit_length() + 7) // 8


def _int_to_b64(value: int, *, length: int | None = None) -> str:
    byte_length = length or _byte_length(value)
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).decode().rstrip("=")


def _b64_to_int(value: str) -> int:
    padding = "=" * (-len(value) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(value + padding), "big")
