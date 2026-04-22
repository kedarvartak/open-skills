# Registry

The registry feature handles local and remote skill distribution.

It contains:

- `store.py`: registry layout creation, publishing, search, install, archive extraction, remote index loading, digest verification, and lockfile writing.

The registry is responsible for moving skill packages between authors, stores, and users. It should not decide how skills activate or how host adapters render context.
