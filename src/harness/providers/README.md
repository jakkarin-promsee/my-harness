# src/harness/providers — the model adapters

The seam between the loop and every vendor. The loop speaks **one** dialect (OpenAI-style messages, one reply shape); each adapter makes its provider look like that, translating **both** directions because history is replayed on every call. Full design + the six-way Anthropic translation table: [docs/notes/03-provider-adapter.md](../../../docs/notes/03-provider-adapter.md).

| File | What it does |
|---|---|
| `base.py` | The `Model` protocol: `complete(messages, tools) -> {message, finish_reason, usage}`. The internal dialect everything else targets. |
| `openai_compat.py` | One adapter for every OpenAI-compatible endpoint — Ollama (local), Gemini, and anything else at a `/v1/chat/completions` URL. Also handles SSE streaming (note 12). |
| `anthropic.py` | The interesting one: `/v1/messages` differs six ways from chat/completions. Pure `to_*` / `from_*` functions do the translation; `complete()` is a thin HTTP shell. Live-untested by constitutional order (`docs/problem.md`). |

**Adding a provider?** If it speaks OpenAI-compat, it's just a new entry in `cli/repl.py`'s `PROVIDERS` (a URL + key + model) — no new adapter. If it has its own dialect, write a `to_*` / `from_*` pair like `anthropic.py` and keep the HTTP in a thin `complete()`. Test the translation offline against a monkeypatched `requests.post` (see `tests/test_anthropic.py`).
