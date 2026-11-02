import json

import httpx
import pytest

from app.llm import LLMError, OpenAICompatibleLLM, ThinkFilter, strip_reasoning


def make_llm(handler) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM("http://llm/v1", "test-model", transport=httpx.MockTransport(handler))


def test_strip_reasoning():
    assert strip_reasoning("<think>je réfléchis</think>\nBonjour") == "Bonjour"


def test_think_filter_across_tokens():
    f = ThinkFilter()
    tokens = ["Avant ", "<think>", "secret ", "encore", "</think>", " Après", " <think>x</think>fin"]
    assert "".join(f.feed(t) for t in tokens) == "Avant  Après fin"


async def test_complete_sends_openai_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "<think>…</think>Réponse"}}]})

    llm = make_llm(handler)
    assert await llm.complete([{"role": "user", "content": "Salut"}]) == "Réponse"
    assert seen["url"] == "http://llm/v1/chat/completions"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["stream"] is False


async def test_stream_parses_server_sent_events():
    chunks = ["Bon", "jour", " !"]
    sse = (
        "".join(f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n" for c in chunks)
        + "data: [DONE]\n\n"
    )

    llm = make_llm(lambda request: httpx.Response(200, text=sse))
    assert [t async for t in llm.stream([])] == chunks


async def test_errors_are_wrapped():
    llm = make_llm(lambda request: httpx.Response(500, text="boom"))
    with pytest.raises(LLMError):
        await llm.complete([])


async def test_ping():
    assert await make_llm(lambda r: httpx.Response(200, json={"data": []})).ping() is True
    assert await make_llm(lambda r: httpx.Response(404)).ping() is False
