import html
import ipaddress
import json
import os
import secrets
import socket
import tempfile
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, quote

import click
import llm
import psutil
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Route

MAX_FORM_SIZE = 64 * 1024


PAGE_TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LLM keys</title>
  <style>
    :root {
      color-scheme: light;
      --background: #f5f5f2;
      --surface: #ffffff;
      --text: #1f2421;
      --muted: #68706b;
      --border: #d9ddd9;
      --accent: #245c43;
      --accent-hover: #194832;
      --focus: #8ab7a0;
      --success-background: #edf7f0;
      --success-border: #a9ceb5;
      --error-background: #fff1ef;
      --error-border: #e3aaa1;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--background);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    main {
      width: min(960px, calc(100% - 32px));
      margin: 0 auto;
      padding: 64px 0;
    }

    header {
      margin-bottom: 32px;
    }

    h1,
    h2,
    p {
      margin-top: 0;
    }

    h1 {
      margin-bottom: 8px;
      font-size: clamp(2rem, 5vw, 3rem);
      letter-spacing: -0.04em;
      line-height: 1.05;
    }

    h2 {
      margin-bottom: 20px;
      font-size: 1rem;
      letter-spacing: -0.01em;
    }

    .intro,
    .hint,
    .empty {
      color: var(--muted);
    }

    .intro {
      max-width: 600px;
      margin-bottom: 0;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: 20px;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface);
      padding: 24px;
      box-shadow: 0 1px 2px rgb(16 24 20 / 5%);
    }

    .panel-heading {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 20px;
    }

    .panel-heading h2 {
      margin-bottom: 0;
    }

    .count {
      color: var(--muted);
      font-size: 0.8125rem;
    }

    .key-list {
      margin: 0;
      padding: 0;
      list-style: none;
      border-top: 1px solid var(--border);
    }

    .key-list li {
      border-bottom: 1px solid var(--border);
    }

    .key-list a {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 13px 10px;
      color: var(--text);
      border-radius: 6px;
      text-decoration: none;
    }

    .key-name {
      min-width: 0;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 0.9rem;
      overflow-wrap: anywhere;
    }

    .key-status {
      flex: 0 0 auto;
      color: var(--muted);
      font-size: 0.75rem;
    }

    .key-list a:hover,
    .key-list a[aria-current="page"] {
      background: #edf2ee;
      color: var(--accent-hover);
    }

    .notice {
      margin-bottom: 20px;
      border: 1px solid;
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 0.9rem;
    }

    .notice.success {
      border-color: var(--success-border);
      background: var(--success-background);
    }

    .notice.error {
      border-color: var(--error-border);
      background: var(--error-background);
    }

    .field {
      margin-bottom: 20px;
    }

    label {
      display: block;
      margin-bottom: 7px;
      font-size: 0.875rem;
      font-weight: 650;
    }

    input {
      width: 100%;
      min-height: 44px;
      border: 1px solid #b9bfbb;
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      padding: 10px 12px;
      font: inherit;
    }

    input:focus-visible,
    a:focus-visible,
    button:focus-visible {
      outline: 3px solid var(--focus);
      outline-offset: 2px;
    }

    .hint {
      margin: 7px 0 0;
      font-size: 0.8125rem;
    }

    button {
      min-height: 44px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      padding: 10px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover {
      background: var(--accent-hover);
    }

    @media (max-width: 720px) {
      main {
        width: min(100% - 24px, 560px);
        padding: 36px 0;
      }

      .layout {
        grid-template-columns: 1fr;
      }

      .panel {
        padding: 20px;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>LLM keys</h1>
      <p class="intro">Set keys for installed models or add another name. Existing values are never displayed.</p>
    </header>

    $notice

    <div class="layout">
      <section class="panel" aria-labelledby="key-names-heading">
        <div class="panel-heading">
          <h2 id="key-names-heading">Key names</h2>
          <span class="count">$key_count</span>
        </div>
        $key_list
      </section>

      <section class="panel" aria-labelledby="set-key-heading">
        <h2 id="set-key-heading">Set a key</h2>
        <form action="/keys" method="post">
          <input type="hidden" name="csrf_token" value="$csrf_token">
          <div class="field">
            <label for="name">Key name</label>
            <input id="name" name="name" value="$selected_name" maxlength="200" required autocomplete="off" spellcheck="false">
            <p class="hint">Choose a listed key or enter any name.</p>
          </div>
          <div class="field">
            <label for="value">New value</label>
            <input id="value" name="value" type="password" required autocomplete="new-password" spellcheck="false">
          </div>
          <button type="submit">Save key</button>
        </form>
      </section>
    </div>
  </main>
</body>
</html>
"""
)


class KeyStoreError(Exception):
    """Raised when the LLM key store cannot be read or written."""


def _load_keys(path: Path) -> dict[str, str]:
    try:
        if not path.exists():
            return {}
        keys = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        raise KeyStoreError from ex
    if not isinstance(keys, dict):
        raise KeyStoreError
    return keys


def _key_names(path: Path) -> list[str]:
    return sorted(_load_keys(path))


def _installed_model_key_names() -> list[str]:
    names = set()
    for model_with_aliases in llm.get_models_with_aliases():
        for model in (model_with_aliases.model, model_with_aliases.async_model):
            if model is not None:
                name = getattr(model, "needs_key", None)
                if isinstance(name, str) and _validate_name(name) is None:
                    names.add(name)
    for model_with_aliases in llm.get_embedding_models_with_aliases():
        name = getattr(model_with_aliases.model, "needs_key", None)
        if isinstance(name, str) and _validate_name(name) is None:
            names.add(name)
    return sorted(names, key=lambda name: (name.casefold(), name))


def _key_state(
    path: Path, model_key_names: frozenset[str]
) -> tuple[list[str], set[str]]:
    stored_names = set(_key_names(path))
    all_names = sorted(
        model_key_names | stored_names, key=lambda name: (name.casefold(), name)
    )
    return all_names, stored_names


def _set_key(path: Path, name: str, value: str) -> None:
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = _load_keys(path)
        keys[name] = value
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}."
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(keys, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary_path.chmod(0o600)
        os.replace(temporary_path, path)
        path.chmod(0o600)
    except KeyStoreError:
        raise
    except OSError as ex:
        raise KeyStoreError from ex
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _validate_name(name: str) -> str | None:
    if not name:
        return "Enter a key name."
    if len(name) > 200:
        return "Key names must be 200 characters or fewer."
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        return "Key names cannot contain control characters."
    return None


def _security_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _plain_error(message: str, status_code: int) -> Response:
    return _security_headers(PlainTextResponse(message, status_code=status_code))


def _render_page(
    key_names: list[str],
    stored_key_names: set[str],
    csrf_token: str,
    *,
    selected_name: str = "",
    saved_name: str | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    if error:
        notice = f'<div class="notice error" role="alert">{html.escape(error)}</div>'
    elif saved_name:
        notice = (
            '<div class="notice success" role="status">Saved '
            f"<strong>{html.escape(saved_name)}</strong>.</div>"
        )
    else:
        notice = ""

    if key_names:
        items = []
        for name in key_names:
            current = ' aria-current="page"' if name == selected_name else ""
            status = "Stored" if name in stored_key_names else "Not stored"
            items.append(
                f'<li><a href="/?name={quote(name, safe="")}"{current}>'
                f'<span class="key-name">{html.escape(name)}</span>'
                f'<span class="key-status">{status}</span></a></li>'
            )
        key_list = f'<ul class="key-list">{"".join(items)}</ul>'
    else:
        key_list = '<p class="empty">No key names found.</p>'

    count = len(key_names)
    body = PAGE_TEMPLATE.substitute(
        notice=notice,
        key_count=f"{count} name" if count == 1 else f"{count} names",
        key_list=key_list,
        csrf_token=html.escape(csrf_token, quote=True),
        selected_name=html.escape(selected_name, quote=True),
    )
    return _security_headers(HTMLResponse(body, status_code=status_code))


def create_app(
    *,
    keys_path: Path | None = None,
    csrf_token: str | None = None,
    model_key_names: list[str] | None = None,
) -> Starlette:
    """Create the Starlette application used by the ``llm key-ui`` command."""

    resolved_keys_path = keys_path or (llm.user_dir() / "keys.json")
    resolved_csrf_token = csrf_token or secrets.token_urlsafe(32)
    discovered_names = (
        _installed_model_key_names()
        if model_key_names is None
        else [
            name
            for name in model_key_names
            if isinstance(name, str) and _validate_name(name) is None
        ]
    )
    resolved_model_key_names = frozenset(discovered_names)

    async def homepage(request: Request) -> Response:
        try:
            names, stored_names = _key_state(
                resolved_keys_path, resolved_model_key_names
            )
        except KeyStoreError:
            return _render_page(
                sorted(
                    resolved_model_key_names,
                    key=lambda name: (name.casefold(), name),
                ),
                set(),
                resolved_csrf_token,
                error="The LLM key store could not be read.",
                status_code=500,
            )

        requested_name = request.query_params.get("name", "")
        selected_name = requested_name if requested_name in names else ""
        saved = request.query_params.get("saved")
        saved_name = saved if saved in names else None
        if saved_name:
            selected_name = saved_name
        return _render_page(
            names,
            stored_names,
            resolved_csrf_token,
            selected_name=selected_name,
            saved_name=saved_name,
        )

    async def update_key(request: Request) -> Response:
        content_type = request.headers.get("content-type", "").split(";", 1)[0]
        if content_type != "application/x-www-form-urlencoded":
            names, stored_names = _safe_key_state(
                resolved_keys_path, resolved_model_key_names
            )
            return _render_page(
                names,
                stored_names,
                resolved_csrf_token,
                error="Unsupported form submission.",
                status_code=415,
            )

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_FORM_SIZE:
                    return _plain_error("Form submission is too large.", 413)
            except ValueError:
                return _plain_error("Invalid request.", 400)

        body = await request.body()
        if len(body) > MAX_FORM_SIZE:
            return _plain_error("Form submission is too large.", 413)
        try:
            fields = parse_qs(
                body.decode("utf-8"), keep_blank_values=True, max_num_fields=10
            )
        except (UnicodeDecodeError, ValueError):
            return _plain_error("Invalid form submission.", 400)

        submitted_token = fields.get("csrf_token", [""])[-1]
        if not secrets.compare_digest(submitted_token, resolved_csrf_token):
            names, stored_names = _safe_key_state(
                resolved_keys_path, resolved_model_key_names
            )
            return _render_page(
                names,
                stored_names,
                resolved_csrf_token,
                error="The form expired. Refresh the page and try again.",
                status_code=403,
            )

        name = fields.get("name", [""])[-1].strip()
        value = fields.get("value", [""])[-1]
        validation_error = _validate_name(name)
        if validation_error or not value:
            names, stored_names = _safe_key_state(
                resolved_keys_path, resolved_model_key_names
            )
            return _render_page(
                names,
                stored_names,
                resolved_csrf_token,
                selected_name=name,
                error=validation_error or "Enter a key value.",
                status_code=400,
            )

        try:
            _set_key(resolved_keys_path, name, value)
        except KeyStoreError:
            names, stored_names = _safe_key_state(
                resolved_keys_path, resolved_model_key_names
            )
            return _render_page(
                names,
                stored_names,
                resolved_csrf_token,
                selected_name=name,
                error="The LLM key store could not be updated.",
                status_code=500,
            )

        return _security_headers(
            RedirectResponse(url=f"/?saved={quote(name, safe='')}", status_code=303)
        )

    return Starlette(
        debug=False,
        routes=[
            Route("/", homepage, methods=["GET"]),
            Route("/keys", update_key, methods=["POST"]),
        ],
    )


def _safe_key_state(
    path: Path, model_key_names: frozenset[str]
) -> tuple[list[str], set[str]]:
    try:
        return _key_state(path, model_key_names)
    except KeyStoreError:
        return (
            sorted(model_key_names, key=lambda name: (name.casefold(), name)),
            set(),
        )


def _interface_ipv4_addresses() -> list[str]:
    addresses = {
        address.address
        for interface_addresses in psutil.net_if_addrs().values()
        for address in interface_addresses
        if address.family == socket.AF_INET
    }
    if not addresses:
        addresses.add("127.0.0.1")
    return sorted(addresses, key=ipaddress.IPv4Address)


def _print_interface_urls(port: int) -> None:
    click.echo("Available URLs:")
    for address in _interface_ipv4_addresses():
        click.echo(f"  http://{address}:{port}/")


@llm.hookimpl
def register_commands(cli):
    @cli.command(name="key-ui", context_settings={"help_option_names": ["--help"]})
    @click.option(
        "-p",
        "--port",
        type=click.IntRange(1, 65535),
        default=8010,
        show_default=True,
        help="Port for the server.",
    )
    @click.option(
        "-h",
        "--host",
        default="127.0.0.1",
        show_default=True,
        help="Host interface for the server.",
    )
    @click.option(
        "--all",
        "all_interfaces",
        is_flag=True,
        help="Listen on all IPv4 interfaces and print their URLs.",
    )
    def key_ui(port: int, host: str, all_interfaces: bool) -> None:
        """Start the local LLM key management UI."""

        if all_interfaces:
            host = "0.0.0.0"
            _print_interface_urls(port)
        uvicorn.run(create_app(), host=host, port=port)
