#!/usr/bin/env python3
"""Generate the browser-safe API catalogue from the committed OpenAPI contract."""
from __future__ import annotations
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "contracts" / "openapi.yaml"
TARGET = Path(__file__).resolve().parents[1] / "src" / "api" / "generated" / "catalog.json"
TS_TARGET = Path(__file__).resolve().parents[1] / "src" / "api" / "generated" / "catalog.ts"

HTTP = {"get", "post", "put", "patch", "delete"}

def compact_schema(schema):
    if not isinstance(schema, dict):
        return schema
    allowed = {"$ref", "type", "format", "title", "description", "enum", "nullable", "readOnly", "writeOnly", "default", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern"}
    out = {k: v for k, v in schema.items() if k in allowed}
    if "properties" in schema:
        out["properties"] = {k: compact_schema(v) for k, v in schema["properties"].items()}
    if "required" in schema:
        out["required"] = schema["required"]
    if "items" in schema:
        out["items"] = compact_schema(schema["items"])
    for key in ("allOf", "oneOf", "anyOf"):
        if key in schema:
            out[key] = [compact_schema(v) for v in schema[key]]
    return out

def schema_for_content(content):
    for mime in ("application/json", "multipart/form-data", "application/x-www-form-urlencoded", "application/pdf"):
        if mime in content:
            return compact_schema(content[mime].get("schema", {})), mime
    return {}, None

def main():
    doc = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    operations = []
    for path, item in doc.get("paths", {}).items():
        shared_parameters = item.get("parameters", [])
        for method, op in item.items():
            if method.lower() not in HTTP:
                continue
            request_schema, request_mime = schema_for_content(op.get("requestBody", {}).get("content", {}))
            response_schema = {}
            response_mime = None
            for status in ("200", "201", "202", "204"):
                response = op.get("responses", {}).get(status)
                if response:
                    response_schema, response_mime = schema_for_content(response.get("content", {}))
                    break
            parameters = []
            for p in [*shared_parameters, *op.get("parameters", [])]:
                parameters.append({
                    "name": p.get("name"),
                    "in": p.get("in"),
                    "required": bool(p.get("required")),
                    "description": p.get("description", ""),
                    "schema": compact_schema(p.get("schema", {})),
                })
            operations.append({
                "id": op.get("operationId"),
                "method": method.upper(),
                "path": path,
                "tag": (op.get("tags") or [""])[0],
                "summary": op.get("summary", ""),
                "description": op.get("description", ""),
                "parameters": parameters,
                "requestSchema": request_schema,
                "requestMime": request_mime,
                "requestRequired": bool(op.get("requestBody", {}).get("required")),
                "responseSchema": response_schema,
                "responseMime": response_mime,
                "statuses": sorted(op.get("responses", {}).keys()),
            })
    payload = {
        "meta": {"title": doc.get("info", {}).get("title"), "version": doc.get("info", {}).get("version"), "source": "../contracts/openapi.yaml"},
        "schemas": {name: compact_schema(schema) for name, schema in doc.get("components", {}).get("schemas", {}).items()},
        "operations": operations,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    TARGET.write_text(compact, encoding="utf-8")
    TS_TARGET.write_text("const catalog = " + compact + " as const;\nexport default catalog;\n", encoding="utf-8")
    print(f"generated {TARGET} and {TS_TARGET} ({len(operations)} operations, {len(payload['schemas'])} schemas)")

if __name__ == "__main__":
    main()
