from unittest.mock import Mock

import pytest

from resume_renderer.services import llm_client


def test_lite_model_uses_same_gemini_key_and_leaves_main_model_unchanged(monkeypatch):
    monkeypatch.setenv("RESUME_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "shared-test-key")
    monkeypatch.setenv("GOOGLE_MODEL", "main-test-model")
    monkeypatch.setenv("GEMINI_MODEL", "legacy-model-must-not-override-google")
    monkeypatch.setenv("ASSIST_MODEL", "lite-test-model")
    constructor = Mock()
    monkeypatch.setattr(llm_client.genai, "Client", constructor)
    main = llm_client.GeminiLLMClient()
    lite = llm_client.GeminiLLMClient(purpose="preprocessing")
    assert main.model == "main-test-model"
    assert lite.model == "lite-test-model"
    assert constructor.call_count == 2
    assert all(
        call.kwargs == {"api_key": "shared-test-key"}
        for call in constructor.call_args_list
    )


def test_unsupported_provider_raises_error(monkeypatch):
    monkeypatch.setenv("RESUME_LLM_PROVIDER", "azure_openai")
    with pytest.raises(
        llm_client.LLMClientError, match="RESUME_LLM_PROVIDER must be 'gemini'"
    ):
        llm_client.GeminiLLMClient()


def test_lite_requires_explicit_model(monkeypatch):
    monkeypatch.setenv("ASSIST_MODEL", "")
    with pytest.raises(llm_client.LLMClientError, match="ASSIST_MODEL"):
        llm_client.GeminiLLMClient(purpose="preprocessing")


def test_fitter_schema_reaches_gemini_transport_without_network(monkeypatch):
    """Exercise real SDK serialization; mocking generate_content misses this bug."""
    from resume_renderer.services.line_fitter import OPTIMIZATION_SCHEMA

    class RequestPrepared(Exception):
        pass

    monkeypatch.setenv("RESUME_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    client = llm_client.GeminiLLMClient()
    transport = Mock(side_effect=RequestPrepared("Network disabled in test"))
    monkeypatch.setattr(client.client._api_client, "request", transport)
    try:
        with pytest.raises(llm_client.LLMClientError) as caught:
            client.generate_json(
                "Optimize wording.", response_schema=OPTIMIZATION_SCHEMA
            )
        assert isinstance(caught.value.__cause__, RequestPrepared)
        transport.assert_called_once()
    finally:
        client.client.close()


@pytest.mark.parametrize("tier", [0, 1, 2, 3, 4, 5, "1", 1.5, True])
def test_fitter_tiers_remain_integers_from_one_to_four(tier):
    import jsonschema

    from resume_renderer.services.line_fitter import OPTIMIZATION_SCHEMA

    schema = OPTIMIZATION_SCHEMA["properties"]["fixes"]["items"]["properties"]["facts"][
        "properties"
    ]["details"]["items"]["properties"]["tier"]
    if type(tier) is int and 1 <= tier <= 4:
        jsonschema.validate(tier, schema)
    else:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(tier, schema)


@pytest.mark.parametrize("method", ["generate_json", "generate_text"])
def test_provider_status_survives_client_wrapping(monkeypatch, method):
    class BusyError(Exception):
        code = 503

    transport = Mock()
    transport.models.generate_content.side_effect = BusyError("Service busy")
    monkeypatch.setenv("RESUME_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setattr(llm_client.genai, "Client", lambda **kwargs: transport)
    client = llm_client.GeminiLLMClient()
    with pytest.raises(llm_client.LLMClientError) as caught:
        getattr(client, method)("Test prompt")
    assert caught.value.code == 503


def test_gemini_json_schema_omits_openapi_additional_properties(monkeypatch):
    monkeypatch.setenv("RESUME_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    transport = Mock()
    transport.models.generate_content.return_value = Mock(text='[{"text": "ok"}]')
    monkeypatch.setattr(llm_client.genai, "Client", lambda **kwargs: transport)

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
            "additionalProperties": False,
        },
    }

    result = llm_client.GeminiLLMClient().generate_json(
        "Return the section.", response_schema=schema
    )

    assert result == [{"text": "ok"}]
    sent_schema = transport.models.generate_content.call_args.kwargs[
        "config"
    ].response_schema
    assert "additionalProperties" not in sent_schema["items"]
