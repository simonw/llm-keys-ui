import json
from types import SimpleNamespace

import click
from click.testing import CliRunner
from starlette.testclient import TestClient

import llm_keys_ui


def make_cli():
    @click.group(context_settings={"help_option_names": ["-h", "--help"]})
    def cli():
        pass

    llm_keys_ui.register_commands(cli)
    return cli


def test_plugin_is_installed():
    assert llm_keys_ui


def test_command_uses_default_host_and_port(monkeypatch):
    called = {}

    def fake_run(app, *, host, port):
        called.update(app=app, host=host, port=port)

    monkeypatch.setattr(llm_keys_ui.uvicorn, "run", fake_run)
    result = CliRunner().invoke(make_cli(), ["keys-ui"])

    assert result.exit_code == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8010


def test_command_accepts_short_host_and_port_options(monkeypatch):
    called = {}

    def fake_run(app, *, host, port):
        called.update(app=app, host=host, port=port)

    monkeypatch.setattr(llm_keys_ui.uvicorn, "run", fake_run)
    result = CliRunner().invoke(make_cli(), ["keys-ui", "-h", "0.0.0.0", "-p", "8123"])

    assert result.exit_code == 0
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 8123


def test_all_option_listens_on_every_interface_and_prints_urls(monkeypatch):
    called = {}

    def fake_run(app, *, host, port):
        called.update(app=app, host=host, port=port)

    monkeypatch.setattr(llm_keys_ui.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        llm_keys_ui,
        "_interface_ipv4_addresses",
        lambda: ["127.0.0.1", "192.168.1.20", "100.113.1.114"],
    )

    result = CliRunner().invoke(
        make_cli(),
        ["keys-ui", "--host", "192.0.2.10", "--all", "--port", "8123"],
    )

    assert result.exit_code == 0
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 8123
    assert "http://127.0.0.1:8123/" in result.output
    assert "http://192.168.1.20:8123/" in result.output
    assert "http://100.113.1.114:8123/" in result.output


def test_key_names_are_collected_from_sync_async_and_embedding_models(monkeypatch):
    regular_models = [
        SimpleNamespace(
            model=SimpleNamespace(needs_key="openai"),
            async_model=SimpleNamespace(needs_key="anthropic"),
        ),
        SimpleNamespace(
            model=SimpleNamespace(needs_key=None),
            async_model=None,
        ),
    ]
    embedding_models = [
        SimpleNamespace(model=SimpleNamespace(needs_key="openai")),
        SimpleNamespace(model=SimpleNamespace(needs_key="cohere")),
    ]
    monkeypatch.setattr(
        llm_keys_ui.llm, "get_models_with_aliases", lambda: regular_models
    )
    monkeypatch.setattr(
        llm_keys_ui.llm,
        "get_embedding_models_with_aliases",
        lambda: embedding_models,
    )

    assert llm_keys_ui._installed_model_key_names() == [
        "anthropic",
        "cohere",
        "openai",
    ]


def test_page_merges_model_and_stored_names_but_never_values(tmp_path):
    keys_path = tmp_path / "keys.json"
    keys_path.write_text(
        json.dumps(
            {
                "openai": "openai-secret-value",
                "private-model": "private-secret-value",
            }
        )
    )
    client = TestClient(
        llm_keys_ui.create_app(
            keys_path=keys_path,
            csrf_token="test-token",
            model_key_names=["anthropic", "openai"],
        )
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "anthropic" in response.text
    assert "openai" in response.text
    assert "private-model" in response.text
    assert "openai-secret-value" not in response.text
    assert "private-secret-value" not in response.text
    assert response.text.count(">Stored</span>") == 2
    assert response.text.count(">Not stored</span>") == 1
    assert response.headers["cache-control"] == "no-store"


def test_existing_key_can_be_updated_without_rendering_value(tmp_path):
    keys_path = tmp_path / "keys.json"
    keys_path.write_text(json.dumps({"openai": "old-secret"}))
    client = TestClient(
        llm_keys_ui.create_app(
            keys_path=keys_path,
            csrf_token="test-token",
            model_key_names=["openai"],
        )
    )

    response = client.post(
        "/keys",
        data={
            "csrf_token": "test-token",
            "name": "openai",
            "value": "replacement-secret",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "replacement-secret" not in response.text
    assert json.loads(keys_path.read_text())["openai"] == "replacement-secret"
    assert keys_path.stat().st_mode & 0o777 == 0o600

    page = client.get(response.headers["location"])
    assert page.status_code == 200
    assert "Saved <strong>openai</strong>" in page.text
    assert "old-secret" not in page.text
    assert "replacement-secret" not in page.text


def test_new_key_can_be_added(tmp_path):
    keys_path = tmp_path / "keys.json"
    client = TestClient(
        llm_keys_ui.create_app(
            keys_path=keys_path, csrf_token="test-token", model_key_names=[]
        )
    )

    response = client.post(
        "/keys",
        data={
            "csrf_token": "test-token",
            "name": "new-provider",
            "value": "new-secret",
        },
        follow_redirects=False,
    )

    stored = json.loads(keys_path.read_text())
    assert response.status_code == 303
    assert stored["new-provider"] == "new-secret"
    assert stored == {"new-provider": "new-secret"}


def test_post_requires_csrf_token(tmp_path):
    keys_path = tmp_path / "keys.json"
    client = TestClient(
        llm_keys_ui.create_app(
            keys_path=keys_path, csrf_token="test-token", model_key_names=[]
        )
    )

    response = client.post(
        "/keys", data={"name": "openai", "value": "must-not-be-saved"}
    )

    assert response.status_code == 403
    assert "must-not-be-saved" not in response.text
    assert not keys_path.exists()


def test_validation_error_does_not_render_submitted_value(tmp_path):
    client = TestClient(
        llm_keys_ui.create_app(
            keys_path=tmp_path / "keys.json",
            csrf_token="test-token",
            model_key_names=[],
        )
    )

    response = client.post(
        "/keys",
        data={
            "csrf_token": "test-token",
            "name": "",
            "value": "must-not-be-rendered",
        },
    )

    assert response.status_code == 400
    assert "Enter a key name." in response.text
    assert "must-not-be-rendered" not in response.text
