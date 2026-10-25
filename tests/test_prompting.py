from unittest.mock import Mock

import pytest
import requests

from src.oracle_gen.prompting import fetch_wikipedia_text
from src.project_config import USER_AGENT


ARTICLE = "Source introduction.\n\n== Distribution and habitat ==\nGeographic evidence from a later section."


def article_response(payload):
    response = Mock()
    response.json.return_value = payload
    return response


@pytest.mark.parametrize("url,title", [
    ("https://en.wikipedia.org/wiki/Sunda_pangolin", "Sunda pangolin"),
    ("https://en.wikipedia.org/wiki/Raffles%27_banded_langur#Distribution", "Raffles' banded langur"),
    ("https://en.wikipedia.org/wiki/Manis_javanica?oldformat=true", "Manis javanica"),
])
def test_fetch_keeps_later_sections_and_handles_article_urls(monkeypatch, url, title):
    # Simulate a resolved redirect as returned by MediaWiki.
    response = article_response({"query": {
        "redirects": [{"from": "Manis javanica", "to": "Sunda pangolin"}],
        "pages": [{"pageid": 123, "title": "Sunda pangolin", "extract": ARTICLE}],
    }})
    get = Mock(return_value=response)
    monkeypatch.setattr("src.oracle_gen.prompting.requests.get", get)

    assert fetch_wikipedia_text(url, timeout=12) == ARTICLE
    response.raise_for_status.assert_called_once()
    assert get.call_args.args == ("https://en.wikipedia.org/w/api.php",)
    options = get.call_args.kwargs
    assert options["timeout"] == 12
    assert options["headers"] == {"User-Agent": USER_AGENT}
    params = options["params"]
    assert params["titles"] == title
    assert params["redirects"] == 1
    assert params["explaintext"] == 1
    assert params["formatversion"] == 2
    assert not {"exintro", "exchars", "exsentences"} & params.keys()


@pytest.mark.parametrize("payload,message", [
    ({"error": {"code": "badvalue", "info": "Bad request"}}, "Bad request"),
    ({"query": {"pages": [{"title": "Missing", "missing": True}]}}, "not found"),
    ({"query": {"pages": []}}, "not found"),
    ({"query": {"pages": [{"title": "Empty", "extract": "  \n"}]}}, "no article text"),
    ({"query": {"pages": [{"title": "No extract"}]}}, "no article text"),
])
def test_failed_article_retrieval_does_not_silently_supply_empty_knowledge(monkeypatch, payload, message):
    monkeypatch.setattr("src.oracle_gen.prompting.requests.get", Mock(return_value=article_response(payload)))
    with pytest.raises(ValueError, match=message):
        fetch_wikipedia_text("https://en.wikipedia.org/wiki/Sunda_pangolin")


def test_http_errors_propagate(monkeypatch):
    response = article_response({})
    response.raise_for_status.side_effect = requests.HTTPError("Unavailable")
    monkeypatch.setattr("src.oracle_gen.prompting.requests.get", Mock(return_value=response))
    with pytest.raises(requests.HTTPError):
        fetch_wikipedia_text("https://en.wikipedia.org/wiki/Sunda_pangolin")


def test_invalid_url_fails_before_network_request(monkeypatch):
    get = Mock()
    monkeypatch.setattr("src.oracle_gen.prompting.requests.get", get)
    with pytest.raises(ValueError, match="Wikipedia article URL"):
        fetch_wikipedia_text("https://example.test/Sunda_pangolin")
    get.assert_not_called()
