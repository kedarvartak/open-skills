# Trust

The trust feature proves package integrity and publisher identity.

It contains:

- `signing.py`: deterministic package digests, public-key generation, package signing, signature reading, and signature verification.

The current pure-Python RSA implementation is for prototyping the trust contract. Production use should replace it with an audited signing stack while preserving the public API and registry metadata shape.
