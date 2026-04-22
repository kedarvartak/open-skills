"""Package digest and signing support."""

from .signing import (
    SIGNATURE_ALGORITHM,
    SIGNATURE_FILE,
    PackageSignature,
    SignatureVerification,
    SigningError,
    compute_package_digest,
    generate_keypair,
    public_key_id,
    read_signature,
    sign_package,
    verify_package_signature,
)

__all__ = [
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_FILE",
    "PackageSignature",
    "SignatureVerification",
    "SigningError",
    "compute_package_digest",
    "generate_keypair",
    "public_key_id",
    "read_signature",
    "sign_package",
    "verify_package_signature",
]
