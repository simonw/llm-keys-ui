# llm-key-ui

[![PyPI](https://img.shields.io/pypi/v/llm-key-ui.svg)](https://pypi.org/project/llm-key-ui/)

A local web UI for setting keys used by [LLM](https://llm.datasette.io/).

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

The `--all` option also listens on `0.0.0.0` and prints an HTTP URL for every
IPv4 address assigned to the computer:

```bash
llm key-ui --all
```

Listening on `0.0.0.0` makes the key-management interface available to other
devices that can reach the computer. The server does not provide authentication.

The interface finds the key names declared by all installed language and
embedding models. It also includes custom names already stored by LLM. Select a
listed name to set its value, or enter any other name to add a key. Existing
values are never displayed.

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
