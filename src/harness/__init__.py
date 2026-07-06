"""researcher-harness — a from-scratch agent harness, grown from mvp/harness.py.

Package layout mirrors the concerns every mature harness separates
(see docs/notes/02-package-structure.md):

    core/       the agent loop (provider-agnostic, fully testable offline)
    providers/  HTTP clients that normalize each provider's dialect
    tools/      tool implementations + their JSON-schema advertisements
    cli/        the REPL, permission gate, token meter — everything human-facing
"""
