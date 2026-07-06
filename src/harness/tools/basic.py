"""The core tool set: implementation + JSON-schema advertisement.

A tool = a plain local function (what actually runs) + a schema (all the
model ever sees). The model cannot execute anything — it *asks* by replying
with tool_calls; the loop runs the function and mails the result back.

Tool descriptions matter more than they look: they are the ONLY signal the
model has for choosing tools (the SWE-agent "ACI" lesson — Stage 2.2 topic).
"""

import json
import os
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import requests

# Directories no search should ever descend into.
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "sessions"}


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"wrote {len(content)} chars to {path}"


def list_dir(path: str) -> str:
    return json.dumps(sorted(os.listdir(path)))


def run_shell(command: str) -> str:
    # shell=True on Windows means cmd.exe. The timeout is load-bearing:
    # without it, one hung command hangs the whole agent turn forever.
    proc = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=60
    )
    return f"exit code: {proc.returncode}\n{proc.stdout or ''}{proc.stderr or ''}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    # The uniqueness rule (Claude Code's Edit, aider's search/replace):
    # ambiguity becomes an error the MODEL can fix by adding context,
    # never a silent wrong edit.
    text = read_file(path)
    count = text.count(old_string)
    if count == 0:
        return f"ERROR: old_string not found in {path}. Read the file and copy the text exactly."
    if count > 1:
        return f"ERROR: old_string appears {count} times in {path}. Add surrounding context to make it unique."
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(old_string, new_string, 1))
    return f"edited {path}: 1 replacement"


def grep(pattern: str, path: str = ".") -> str:
    # Bounded, structured search — SWE-agent's lesson: unbounded output
    # wrecks agents. Cap matches, skip junk dirs and binary-ish files.
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: bad regex: {e}"
    matches: list[str] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            fp = os.path.join(root, name)
            try:
                if os.path.getsize(fp) > 1_000_000:
                    continue
                with open(fp, "r", encoding="utf-8", errors="strict") as f:
                    for lineno, line in enumerate(f, 1):
                        if rx.search(line):
                            matches.append(f"{fp}:{lineno}: {line.rstrip()}")
                            if len(matches) >= 50:
                                return "\n".join(matches) + "\n[stopped at 50 matches]"
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable -> not our problem
    return "\n".join(matches) or "no matches"


def glob(pattern: str, path: str = ".") -> str:
    # Newest first — recency is relevance (Claude Code's ordering).
    found = [p for p in Path(path).glob(pattern) if p.is_file()]
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return json.dumps([str(p) for p in found[:100]])


# --- web_fetch (note 19) ---------------------------------------------------
# Bounds copied from opencode's webfetch (timeout) and right-sized for our
# 8K window (download cap, output cap). The loop's 2,000-char diet still
# applies on top — two belts, deliberately.
WEB_TIMEOUT = 30            # seconds (opencode's DEFAULT_TIMEOUT)
WEB_MAX_BYTES = 2_000_000   # stop downloading past this (opencode caps at 5 MB)
WEB_MAX_CHARS = 8_000       # head+tail cap on the extracted text

# The requests default UA ("python-requests/x") is 403'd all over the web;
# every senior ships a browser string (opencode retries with a plain one).
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class _TextExtractor(HTMLParser):
    """HTML -> readable text with the stdlib parser (tolerant of broken
    markup, zero new dependencies). Skips the tags that are never prose,
    breaks lines at block tags; whitespace collapse happens after."""

    SKIP = {"script", "style", "noscript", "template", "iframe", "head"}
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section",
             "article", "header", "footer", "blockquote", "pre",
             "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0  # depth inside SKIP tags (they can nest)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skipping += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skipping = max(0, self._skipping - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skipping:
            self.parts.append(data)


def _html_to_text(body: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(body)
    text = "".join(extractor.parts)
    # Collapse: runs of spaces/tabs -> one space, 2+ blank lines -> one.
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if title:
        text = f"Title: {' '.join(title.group(1).split())}\n\n{text}"
    return text


def _head_tail(text: str, cap: int) -> str:
    # Same ¾ + ¼ split as the loop's _truncate: the tail matters too.
    if len(text) <= cap:
        return text
    head, tail = cap * 3 // 4, cap - cap * 3 // 4
    dropped = len(text) - head - tail
    return text[:head] + f"\n[... {dropped} chars truncated ...]\n" + text[-tail:]


def web_fetch(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return f"ERROR: only http(s) URLs are supported, got {url!r}"
    try:
        resp = requests.get(
            url, timeout=WEB_TIMEOUT, stream=True,
            headers={"User-Agent": WEB_USER_AGENT},
        )
        try:
            if resp.status_code >= 400:
                return f"ERROR: HTTP {resp.status_code} {resp.reason} for {url}"
            ctype = resp.headers.get("content-type", "").lower()
            if ctype and not any(t in ctype for t in ("text", "html", "json", "xml")):
                return f"ERROR: unsupported content type {ctype!r} (binary?)"
            # Stream up to the byte cap so a giant file never fully lands here.
            chunks, size = [], 0
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                size += len(chunk)
                if size >= WEB_MAX_BYTES:
                    break
        finally:
            resp.close()
    except requests.RequestException as e:  # covers connect AND mid-stream drops
        return f"ERROR: fetch failed: {e}"
    body = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
    sniff = body.lstrip()[:200].lower()
    if "html" in ctype or sniff.startswith(("<!doctype", "<html")):
        body = _html_to_text(body)
    return _head_tail(body.strip(), WEB_MAX_CHARS) or "(empty page)"


REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_shell": run_shell,
    "edit_file": edit_file,
    "grep": grep,
    "glob": glob,
    "web_fetch": web_fetch,
}

# The y/N gate: the mutating three, plus web_fetch (read-only for the
# machine, but it's network egress — it asks; note 19).
NEEDS_PERMISSION = {"write_file", "run_shell", "edit_file", "web_fetch"}


def _schema(name: str, desc: str, props: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


SCHEMAS = [
    _schema(
        "read_file",
        "Read a text file and return its full contents.",
        {"path": {"type": "string", "description": "File path, relative to the working directory."}},
        ["path"],
    ),
    _schema(
        "write_file",
        "Create or overwrite a text file with the given content.",
        {
            "path": {"type": "string", "description": "File path to write."},
            "content": {"type": "string", "description": "The full file content."},
        },
        ["path", "content"],
    ),
    _schema(
        "list_dir",
        "List the names of all files and folders in a directory.",
        {"path": {"type": "string", "description": "Directory path, e.g. '.' for the current one."}},
        ["path"],
    ),
    _schema(
        "run_shell",
        "Run a shell command (Windows cmd.exe) and return its exit code and output.",
        {"command": {"type": "string", "description": "The command line to run."}},
        ["command"],
    ),
    _schema(
        "edit_file",
        "Replace text in a file. old_string must match EXACTLY ONCE; if it appears "
        "zero or multiple times you get an error - add surrounding context to disambiguate.",
        {
            "path": {"type": "string", "description": "File to edit."},
            "old_string": {"type": "string", "description": "Exact text to replace (must be unique in the file)."},
            "new_string": {"type": "string", "description": "Replacement text."},
        },
        ["path", "old_string", "new_string"],
    ),
    _schema(
        "grep",
        "Search file contents with a regex. Returns 'path:line_number: line' matches, max 50.",
        {
            "pattern": {"type": "string", "description": "Regular expression to search for."},
            "path": {"type": "string", "description": "Directory to search, default '.'"},
        },
        ["pattern"],
    ),
    _schema(
        "glob",
        "Find files by name pattern (e.g. '**/*.py'). Returns paths, newest first, max 100.",
        {
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py' or 'src/*.toml'."},
            "path": {"type": "string", "description": "Base directory, default '.'"},
        },
        ["pattern"],
    ),
    _schema(
        "web_fetch",
        "Fetch a web page over HTTP GET and return its readable text (HTML tags "
        "stripped, whitespace collapsed, output truncated). Use it to look up "
        "documentation or online resources when a URL is known.",
        {"url": {"type": "string", "description": "Full http(s) URL to fetch."}},
        ["url"],
    ),
]
