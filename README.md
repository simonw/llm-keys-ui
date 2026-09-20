# llm-key-ui

[![PyPI](https://img.shields.io/pypi/v/llm-key-ui.svg)](https://pypi.org/project/llm-key-ui/)

A local web UI for setting keys used by [LLM](https://llm.datasette.io/).

This plugin is particularly useful if you are running a coding agent on a remote machine and want to set some API keys without pasting them into the agent context.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```bash
llm install llm-key-ui
```

## Usage

Start the server on `127.0.0.1:8010`:

```bash
llm key-ui
```

The port can be changed with `-p` or `--port`:

```bash
llm key-ui -p 8080
```

Use `-h` or `--host` to listen on a different interface:

```bash
llm key-ui -h 0.0.0.0
```

The `--all` option also listens on `0.0.0.0` and prints an HTTP URL for every IPv4 address assigned to the computer:

```bash
llm key-ui --all
```

Use this if you want to set keys for a machine accessible via your local network or over Tailscale.

The interface does not implement authentication. Stop the server once you have set your keys.

Existing key values cannot be read using this tool.

## Development

To set up this plugin locally, first checkout the code. Then run the tests with `uv`:

```bash
cd llm-key-ui
uv run pytest
```

To run LLM with your in-development plugin:

```bash
uv run llm --help
```
