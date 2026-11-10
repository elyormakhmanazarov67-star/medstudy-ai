"""Safe, idempotent Qdrant Cloud collection bootstrap for MedStudy AI.

Reads QDRANT_URL and QDRANT_API_KEY from environment variables. Do not share
credentials in chat, commits, browser JavaScript, or command-line arguments.
Creates an EMPTY collection, never deletes data, and never sends user records.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlsplit

import httpx

COLLECTION = "medstudy_lessons_v1"
VECTOR_SIZE = 384
DISTANCE = "Cosine"


def validate_endpoint(raw: str) -> str:
    """Use HTTPS with a Qdrant Cloud database endpoint only."""
    url = raw.strip().rstrip("/")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if (
        parts.scheme != "https"
        or not host.endswith(".cloud.qdrant.io")
        or host == ".cloud.qdrant.io"
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("QDRANT_URL must be a Qdrant Cloud HTTPS database endpoint.")
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("QDRANT_URL has an invalid port.") from exc
    if port not in (None, 443, 6333):
        raise ValueError("QDRANT_URL port must be 443 or 6333.")
    return url


def collection_config() -> dict:
    return {"vectors": {"size": VECTOR_SIZE, "distance": DISTANCE, "on_disk": True}}


def check_schema(data: dict) -> dict:
    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("Qdrant collection metadata is invalid.")
    vectors = (result.get("config") or {}).get("params", {}).get("vectors")
    if not isinstance(vectors, dict) or vectors.get("size") != VECTOR_SIZE or vectors.get("distance") != DISTANCE:
        raise ValueError(
            "Existing collection has different vector dimensions or metric. "
            "It was not modified."
        )
    return {
        "collection": COLLECTION,
        "exists": True,
        "size": VECTOR_SIZE,
        "distance": DISTANCE,
        "points": result.get("points_count"),
        "status": result.get("status"),
    }


def ensure_collection(client: httpx.Client, *, create: bool = False) -> dict:
    path = "/collections/" + COLLECTION
    try:
        response = client.get(path)
        if response.status_code == 404:
            if not create:
                return {"collection": COLLECTION, "exists": False}
            response = client.put(path, json=collection_config())
            if response.status_code in (401, 403):
                raise ValueError("Qdrant API key has no write permission or is expired.")
            if response.status_code >= 400:
                raise ValueError(f"Collection creation failed: HTTP {response.status_code}.")
            response = client.get(path)
        if response.status_code in (401, 403):
            raise ValueError("Qdrant API key is missing, invalid or expired.")
        if response.status_code >= 400:
            raise ValueError(f"Collection status failed: HTTP {response.status_code}.")
        return check_schema(response.json())
    except httpx.RequestError as exc:
        raise ValueError("Cannot connect to Qdrant Cloud. Check endpoint and cluster status.") from exc
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Qdrant returned unreadable metadata.") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("status", "create"), default="status")
    args = parser.parse_args()
    url = validate_endpoint(os.getenv("QDRANT_URL", ""))
    key = os.getenv("QDRANT_API_KEY", "").strip()
    if not key:
        raise SystemExit("QDRANT_API_KEY missing. Add it in GitHub Actions secrets.")
    with httpx.Client(
        base_url=url,
        headers={"api-key": key},
        timeout=12.0,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        result = ensure_collection(client, create=args.mode == "create")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
