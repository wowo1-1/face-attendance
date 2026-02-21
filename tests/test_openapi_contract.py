from __future__ import annotations

from fastapi import FastAPI

from app.api import attend, records, register


def _build_app() -> FastAPI:
    app = FastAPI(title="test-app")
    app.include_router(register.router)
    app.include_router(attend.router)
    app.include_router(records.router)
    return app


def _resolve_ref(openapi: dict, ref: str) -> dict:
    assert ref.startswith("#/"), f"unexpected $ref: {ref}"
    cur = openapi
    for part in ref.lstrip("#/").split("/"):
        cur = cur[part]
    assert isinstance(cur, dict)
    return cur


def test_register_is_multipart_form() -> None:
    app = _build_app()
    spec = app.openapi()

    op = spec["paths"]["/api/register"]["post"]
    content = op["requestBody"]["content"]
    assert "multipart/form-data" in content

    schema = content["multipart/form-data"]["schema"]
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])

    required = set(schema.get("required", []))
    assert {"name", "student_id", "file"} <= required

    props = schema.get("properties", {})
    assert props["name"]["type"] == "string"
    assert props["student_id"]["type"] == "string"
    assert props["file"]["type"] == "string"
    assert props["file"]["format"] == "binary"


def test_attend_is_multipart_form() -> None:
    app = _build_app()
    spec = app.openapi()

    op = spec["paths"]["/api/attend"]["post"]
    content = op["requestBody"]["content"]
    assert "multipart/form-data" in content

    schema = content["multipart/form-data"]["schema"]
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])

    required = set(schema.get("required", []))
    assert {"course_id", "file"} <= required

    props = schema.get("properties", {})
    assert props["course_id"]["type"] == "integer"
    assert props["file"]["type"] == "string"
    assert props["file"]["format"] == "binary"


def test_records_date_query_is_date_format() -> None:
    app = _build_app()
    spec = app.openapi()

    op = spec["paths"]["/api/records"]["get"]
    params = op.get("parameters", [])
    date_param = None
    for p in params:
        if p.get("in") == "query" and p.get("name") == "date":
            date_param = p
            break

    assert date_param is not None, "expected query param 'date' (alias of day)"
    schema = date_param.get("schema", {})
    # Optional query params in OpenAPI 常被表达为 anyOf: [<type>, null]
    candidates = schema.get("anyOf", [schema])
    assert any(
        c.get("type") == "string" and c.get("format") == "date"
        for c in candidates
        if isinstance(c, dict)
    )
