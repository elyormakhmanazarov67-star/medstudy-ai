"""Offline tests only: NEVER access the user's Qdrant Cloud account."""
import json
import unittest

import httpx

from scripts.qdrant_setup import (
    COLLECTION, DISTANCE, VECTOR_SIZE, check_schema,
    collection_config, ensure_collection, validate_endpoint,
)


def collection_response(size=VECTOR_SIZE, distance=DISTANCE):
    return {"result": {
        "config": {"params": {"vectors": {"size": size, "distance": distance}}},
        "status": "green", "points_count": 0,
    }}


class QdrantSetupTests(unittest.TestCase):
    def test_endpoint_rejects_untrusted_domains_and_http(self):
        self.assertEqual(
            validate_endpoint("https://abc.eu-west-2-0.aws.cloud.qdrant.io:6333/"),
            "https://abc.eu-west-2-0.aws.cloud.qdrant.io:6333",
        )
        for invalid in (
            "http://abc.cloud.qdrant.io",
            "https://qdrant.io",
            "https://cloud.qdrant.io.evil.example",
            "https://abc.cloud.qdrant.io/collections",
            "https://user:password@abc.cloud.qdrant.io",
            "https://abc.cloud.qdrant.io:9999",
            "https://abc.cloud.qdrant.io/?action=delete",
            "",
        ):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                validate_endpoint(invalid)

    def test_empty_collection_created_only_when_requested(self):
        requested = []
        exists = False

        def fake(request):
            nonlocal exists
            requested.append(request.method)
            self.assertEqual(request.url.path, "/collections/" + COLLECTION)
            self.assertEqual(request.headers.get("api-key"), "dummy-key")
            if request.method == "GET":
                if exists:
                    return httpx.Response(200, json=collection_response())
                return httpx.Response(404)
            self.assertEqual(request.method, "PUT")
            self.assertEqual(json.loads(request.content), collection_config())
            exists = True
            return httpx.Response(200, json={"result": True})

        with httpx.Client(
            base_url="https://example.cloud.qdrant.io",
            headers={"api-key": "dummy-key"},
            transport=httpx.MockTransport(fake),
        ) as client:
            self.assertFalse(ensure_collection(client)["exists"])
            self.assertFalse(exists)
            created = ensure_collection(client, create=True)
            self.assertTrue(created["exists"])
            self.assertEqual(created["size"], 384)
            ensure_collection(client, create=True)
        self.assertEqual(requested, ["GET", "GET", "PUT", "GET", "GET"])

    def test_never_overwrites_incompatible_collection(self):
        calls = []

        def fake(request):
            calls.append(request.method)
            return httpx.Response(200, json=collection_response(size=768))

        with httpx.Client(
            base_url="https://example.cloud.qdrant.io",
            transport=httpx.MockTransport(fake),
        ) as client:
            with self.assertRaisesRegex(ValueError, "different vector dimensions"):
                ensure_collection(client, create=True)
        self.assertEqual(calls, ["GET"])

    def test_invalid_or_expired_api_key(self):
        with httpx.Client(
            base_url="https://example.cloud.qdrant.io",
            transport=httpx.MockTransport(lambda _: httpx.Response(403, text="some private error")),
        ) as client:
            with self.assertRaisesRegex(ValueError, "invalid or expired"):
                ensure_collection(client, create=True)

    def test_schema_check_returns_safe_metadata_only(self):
        result = check_schema(collection_response())
        self.assertEqual(result["points"], 0)
        self.assertNotIn("api_key", result)


if __name__ == "__main__":
    unittest.main()
