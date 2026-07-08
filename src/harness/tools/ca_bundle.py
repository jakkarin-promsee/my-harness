"""CA-bundle generator for child processes (2.16, note 33).

This machine has TLS interception (archive/labs/02): our own process cures it
with truststore injection, but a *child* process — an MCP server — validates
against certifi's bundle and dies with CERTIFICATE_VERIFY_FAILED (measured on
duckduckgo-mcp-server, 2026-07-08). Children can't inject truststore, but they
honor SSL_CERT_FILE / REQUESTS_CA_BUNDLE — so we write certifi + the Windows
ROOT/CA stores (which hold the interception CA) to one PEM and point the
server's env at it (harness.toml [mcp.servers.*] env).

Regenerate when certs rotate:  uv run python -m harness.tools.ca_bundle
"""

import ssl
from pathlib import Path

import certifi

BUNDLE = Path.home() / ".harness" / "ca-bundle.pem"


def write_bundle(path: Path = BUNDLE) -> int:
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    added = 0
    for store in ("ROOT", "CA"):
        for cert, enc, _ in ssl.enum_certificates(store):
            if enc == "x509_asn":
                pem += "\n" + ssl.DER_cert_to_PEM_cert(cert)
                added += 1
    path.parent.mkdir(exist_ok=True)
    path.write_text(pem, encoding="utf-8")
    return added


if __name__ == "__main__":
    n = write_bundle()
    print(f"wrote {BUNDLE} (certifi + {n} Windows-store certs)")
