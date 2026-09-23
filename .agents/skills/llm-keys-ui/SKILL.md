---
name: llm-keys-ui
description: Save API keys for LLM and its plugins in a local browser page so the secret never enters the chat. Use when a coding agent needs an API key, the user is about to paste a key or token, or keys must be set on a remote, LAN, or Tailscale machine. Run uvx --with llm-keys-ui llm keys-ui --all and share the printed URLs.
license: Apache-2.0
compatibility: Requires uv, or an existing llm install. The key server has no authentication.
metadata:
  short-description: Set LLM keys without pasting them
---

# Set LLM API keys

You need an API key on this machine. The user types it into a browser. The value stays out of the chat.

## Start the server

Run this in the background and wait until it prints URLs:

```bash
uvx --with llm-keys-ui llm keys-ui --all
```

`--all` listens on `0.0.0.0` port 8010 and prints `http://<ipv4>:<port>/` for every IPv4 address on the machine. That includes localhost, LAN addresses, and Tailscale addresses when Tailscale is up.

Send the user every printed URL. `127.0.0.1` is this machine. Addresses in `100.64.0.0/10` are usually Tailscale. The page has no login. Anyone who can open a URL can write keys. After the user has saved the key, stop the server.

If port 8010 is taken, run the same command with `-p` and a free port. The printed URLs use that port.

If `uvx` is missing and `llm` is already installed:

```bash
llm install llm-keys-ui
llm keys-ui --all
```

The page lists key names from models installed in that `llm`, plus names already stored. Each row says Stored or Not stored. Existing values are never shown. The user can type a name that is not in the list. Tell them the name you need, such as `openai` or `anthropic`.

To show a plugin's key name on the page, add that plugin to the same command:

```bash
uvx --with llm-keys-ui --with llm-anthropic llm keys-ui --all
```

Keys land in this user's LLM `keys.json`. A later `llm` on this machine reads that file, including an `llm` that is not the `uvx` copy.

## Use the key

When the user says the key is saved, confirm the name with `llm keys list`. That command prints names only.

Pass the value straight into the command that needs it:

```bash
ANTHROPIC_API_KEY="$(llm keys get anthropic)" some-command
```

Do not run `llm keys get` on its own. Its stdout is the secret. Do not read `keys.json`. Do not put the secret in `llm keys set --value`, a file you write, or your reply.

If `llm keys list` already includes the name, skip the server and use `llm keys get` the same way.

When the user is on this machine and does not need a phone or another device, bind only loopback:

```bash
uvx --with llm-keys-ui llm keys-ui
```

That listens on `127.0.0.1:8010` and prints no URL. Give the user `http://127.0.0.1:8010/`.
