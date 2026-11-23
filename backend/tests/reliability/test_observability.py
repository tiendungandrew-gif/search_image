import json
import logging

from app.core.logging import JSONFormatter


def test_search_trace_fields_are_logged_without_untrusted_extra_data():
    event = logging.LogRecord("app.access", logging.INFO, "fixture", 1, "http_request", (), None)
    event.search_mode = "multi_intent"
    event.model_id = "public-model-id"
    event.index_id = "public-index-id"
    event.route = "multi_vector"
    event.raw_query = "PRIVATE_QUERY"
    event.authorization = "Bearer PRIVATE_TOKEN"
    event.prompt = "PRIVATE_PROMPT"
    value = json.loads(JSONFormatter().format(event))
    assert {key: value[key] for key in ["search_mode", "model_id", "index_id", "route"]} == {
        "search_mode": "multi_intent",
        "model_id": "public-model-id",
        "index_id": "public-index-id",
        "route": "multi_vector",
    }
    assert "PRIVATE_" not in json.dumps(value)
