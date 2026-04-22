# Adapters

The adapters feature converts portable Open Skills packages into host-specific context.

It contains:

- `base.py`: shared adapter context and capability negotiation types.
- `codex.py`: Codex adapter that discovers skills, reuses the shared activation engine, negotiates capabilities, and renders Codex-ready context.

Adapters should stay thin. Shared behavior such as activation, loading, validation, registry access, and trust checks belongs in the dedicated feature folders.
