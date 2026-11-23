"""Real services/CLIP; fictional knowledge is isolated and is not an accuracy benchmark."""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from qdrant_client import models as qm
from sqlalchemy.engine import make_url

from alembic import command
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.db.models.indexing import ActiveSearchIndex
from app.db.models.knowledge import Entity, EntityRelationship
from app.evaluation.agent import evaluate_labeled_cases
from app.main import create_app
from app.repositories.knowledge_import import import_knowledge
from app.schemas.ingestion import ImageMetadataInput
from app.services.embeddings.clip_encoder import ClipEncoder
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, now
from app.services.indexing.worker import Worker

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_AGENT_E2E") != "1",
        reason="Requires migrated stack, real CLIP and RUN_AGENT_E2E=1",
    ),
]


async def test_isolated_empty_services_and_fictional_multihop(monkeypatch):
    base = Settings()
    token = uuid4().hex
    dbname = "agent_test_" + token
    bucket = "agent-test-" + token
    probe_collection = "agent_empty_" + token
    url = make_url(base.database_url.get_secret_value())
    test_url = url.set(database=dbname)

    def create_database():
        with psycopg.connect(
            url.set(database="postgres", drivername="postgresql").render_as_string(
                hide_password=False
            ),
            autocommit=True,
        ) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))

    await asyncio.to_thread(create_database)
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    get_settings.cache_clear()
    cfg = base.model_copy(
        update={
            "app_env": "test",
            "database_url": type(base.database_url)(test_url.render_as_string(hide_password=False)),
            "minio_bucket": bucket,
            "minio_auto_create_bucket": True,
            "search_enabled": False,
            "agent_enabled": True,
            "agent_allow_fixture_knowledge": True,
            "rag_enabled": False,
            "agent_llm_planning_enabled": os.getenv("RUN_AGENT_LLM_FIXTURE") == "1",
            # Administrative collection creation can exceed the health probe timeout.
            "dependency_timeout_seconds": 10,
        }
    )
    services = Services(cfg)
    index = None
    measurements = {
        "classification": "FICTIONAL_FIXTURE_ON_REAL_INFRASTRUCTURE",
        "real_world_accuracy": None,
    }
    try:
        await asyncio.to_thread(command.upgrade, Config("backend/alembic.ini"), "head")
        await services.initialize()
        await services.qdrant.client.create_collection(
            probe_collection, vectors_config=qm.VectorParams(size=512, distance=qm.Distance.COSINE)
        )
        empty = await services.qdrant.client.query_points(
            probe_collection, query=[1.0] + [0.0] * 511, limit=1
        )
        assert not empty.points
        objects = await services.minio.run(
            lambda: list(services.minio.client.list_objects(bucket, recursive=True))
        )
        assert objects == []
        app = create_app(cfg)
        headers = {"Authorization": "Bearer " + cfg.api_token.get_secret_value()}
        query = "Find landmarks in the city where Fixture Lake Alpha is located"
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", headers=headers
            ) as client,
        ):
            assert (await client.get("/api/v1/health/live")).status_code == 200
            status = await client.get("/api/v1/search/agent/status")
            assert status.json()["initialized"] and len(status.json()["tools"]) == 9
            response = await client.post("/api/v1/search/agent", json={"query": query})
            assert response.status_code == 200
            value = response.json()
            assert (
                value["dataset_status"] == "empty_dataset"
                and value["results"] == []
                and value["status"] == "insufficient_evidence"
            )
            measurements["empty_dataset"] = value
        encoder = await asyncio.to_thread(ClipEncoder, cfg)
        index, _ = await CollectionManager(services).register(encoder, "agent_test_" + token[:8])
        cfg.ingestion_index_id = str(index.id)
        raw = await asyncio.to_thread(Path(cfg.dataset_root, "sample/coffee.png").read_bytes)
        accepted, upload = await ingest(
            services,
            raw,
            ImageMetadataInput(
                source_dataset="phase09-fixture",
                license="CC0-1.0",
                rights_ref="datasets/sample_manifest.json",
            ),
            "agent-fixture-" + token,
            index.id,
        )
        assert accepted == 202
        await Worker(services, encoder, index.id).run(once=True)
        verification = await verify_index(services, index.id, mark_ready=True)
        assert verification["status"] == "pass" and verification["verified_images"] == 1
        async with services.database.sessions() as session, session.begin():
            session.add(
                ActiveSearchIndex(
                    corpus_key="default", index_id=index.id, generation=1, activated_at=now()
                )
            )
        payload = json.loads(
            await asyncio.to_thread(
                Path("evaluation/agent/fixtures/fictional_knowledge.json").read_text
            )
        )
        payload["image_entities"] = [
            {
                "image_id": upload["image_id"],
                "entity_id": payload["entities"][2]["id"],
                "relation": "depicts",
                "source_ref": "fixture://phase09/image-association",
                "verified": True,
            }
        ]
        # Expected values come from the import manifest/upload receipt, before execution.
        expected_fixture = {
            "fixture": True,
            "cases": {
                "positive": {
                    "search_mode": "agent",
                    "tools": [
                        "entity_lookup",
                        "relationship_lookup",
                        "get_related_entities",
                        "semantic_image_search",
                    ],
                    "entity_ids": [e["id"] for e in payload["entities"]],
                    "relationship_ids": [r["id"] for r in payload["relationships"]],
                    "image_ids": [upload["image_id"]],
                    "status": "completed",
                }
            },
        }
        imported = await import_knowledge(services, payload, apply=True)
        assert imported["inserted"] == {"entities": 3, "relationships": 2, "image_entities": 1}
        assert (await import_knowledge(services, payload, apply=True))["inserted"] == {
            "entities": 0,
            "relationships": 0,
            "image_entities": 0,
        }
        cfg.search_enabled = True
        app = create_app(cfg)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=headers,
                timeout=30,
            ) as client,
        ):
            response = await client.post("/api/v1/search/agent", json={"query": query, "top_k": 1})
            assert response.status_code == 200
            value = response.json()
            assert value["status"] == "completed", value
            assert value["tool_calls"] == 4 and value["logical_hops"] == 3
            assert [r["image_id"] for r in value["results"]] == [upload["image_id"]]
            assert (
                len(value["evidence"]) == 2 and value["verification_state"] == "TESTED_WITH_MOCKS"
            )
            assert value["image_associations"][0]["verified"] is True
            measurements["deterministic_multihop"] = value
            measurements["fixture_metrics"] = evaluate_labeled_cases(
                [{"case_id": "positive", "result": value}], expected_fixture
            )
            alias = await client.post(
                "/api/v1/search/agent",
                json={"query": query.replace("Fixture Lake Alpha", "Fixture Lake A"), "top_k": 1},
            )
            assert alias.json()["status"] == "completed"
            missing = await client.post(
                "/api/v1/search/agent",
                json={"query": query.replace("Fixture Lake Alpha", "Missing Fixture Lake")},
            )
            assert (
                missing.json()["status"] == "insufficient_evidence"
                and missing.json()["tool_calls"] == 1
                and not missing.json()["results"]
            )
            injection = await client.post(
                "/api/v1/search/agent",
                json={"query": query.replace("Fixture Lake Alpha", "'; DROP TABLE images; --")},
            )
            assert not injection.json()["results"]
            metadata = await client.post(
                "/api/v1/search/agent",
                json={
                    "query": "metadata fixtures",
                    "mode": "metadata",
                    "filters": {"source_dataset": "phase09-fixture"},
                    "top_k": 1,
                },
            )
            assert metadata.json()["results"][0]["image_id"] == upload["image_id"]
            stream = await client.post(
                "/api/v1/search/agent/stream", json={"query": query, "top_k": 1}
            )
            assert (
                stream.status_code == 200
                and "event: tool_started" in stream.text
                and "event: agent_completed" in stream.text
            )
            assert "api_key" not in stream.text.lower()
            if cfg.agent_llm_planning_enabled:
                llm = await client.post(
                    "/api/v1/search/agent",
                    json={"query": query, "top_k": 1, "planning_mode": "llm"},
                )
                value = llm.json()
                measurements["real_llm_fixture_plan"] = value
                assert value["status"] == "completed", {
                    "status": value["status"],
                    "code": value["error_code"],
                    "attempts": value["planner_attempts"],
                }
                assert (
                    value["planner_attempts"] >= 1
                    and value["results"][0]["image_id"] == upload["image_id"]
                )
            async with services.database.sessions() as session, session.begin():
                relation = await session.get(EntityRelationship, payload["relationships"][0]["id"])
                relation.verified_at = None
            missing_relation = (
                await client.post("/api/v1/search/agent", json={"query": query})
            ).json()
            assert missing_relation["status"] == "insufficient_evidence"
            assert missing_relation["tool_calls"] == 2 and not missing_relation["results"]
            measurements["missing_relationship"] = missing_relation
            async with services.database.sessions() as session, session.begin():
                relation = await session.get(EntityRelationship, payload["relationships"][0]["id"])
                relation.verified_at = now()
                other_city = uuid4()
                session.add(
                    Entity(
                        id=other_city,
                        canonical_name="Fixture City Conflict",
                        name_key="fixture city conflict",
                        entity_type="city",
                        locale="und",
                        aliases=[],
                        provenance={"fixture": True, "source_ref": "fixture://conflict"},
                    )
                )
                await session.flush()
                session.add(
                    EntityRelationship(
                        id=uuid4(),
                        subject_id=relation.subject_id,
                        predicate="located_in",
                        object_id=other_city,
                        source_ref="fixture://conflict",
                        evidence={"fixture": True},
                        verified_at=now(),
                    )
                )
            conflict = (await client.post("/api/v1/search/agent", json={"query": query})).json()
            assert conflict["status"] == "insufficient_evidence" and not conflict["results"]
            assert "CONFLICTING_RELATIONSHIPS" in conflict["warnings"]
            measurements["conflicting_relationships"] = conflict
    finally:
        try:
            if index:
                await services.qdrant.client.delete_collection(index.collection_name)
            else:
                # A timed-out create may have succeeded remotely before register returned.
                for collection in (await services.qdrant.client.get_collections()).collections:
                    if collection.name.startswith("images_agent_test_" + token[:8] + "_"):
                        await services.qdrant.client.delete_collection(collection.name)
            await services.qdrant.client.delete_collection(probe_collection)

            def cleanup_bucket():
                assert bucket.startswith("agent-test-")
                for item in services.minio.client.list_objects(bucket, recursive=True):
                    services.minio.client.remove_object(bucket, item.object_name)
                services.minio.client.remove_bucket(bucket)

            await services.minio.run(cleanup_bucket)
        finally:
            await services.close()
            get_settings.cache_clear()

            def drop_database():
                assert dbname.startswith("agent_test_")
                with psycopg.connect(
                    url.set(database="postgres", drivername="postgresql").render_as_string(
                        hide_password=False
                    ),
                    autocommit=True,
                ) as admin:
                    admin.execute(
                        sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(dbname))
                    )

            await asyncio.to_thread(drop_database)
            report = os.getenv("AGENT_FIXTURE_REPORT")
            if report:
                await asyncio.to_thread(
                    Path(report).write_text,
                    json.dumps(measurements, ensure_ascii=False, indent=2) + "\n",
                )


async def test_live_agent_api_existing_images_and_optional_real_rag():
    cfg = Settings()
    async with AsyncClient(
        base_url=os.getenv("AGENT_TEST_BASE_URL", "http://backend:8000"),
        headers={"Authorization": "Bearer " + cfg.api_token.get_secret_value()},
        timeout=45,
    ) as client:
        direct = await client.post(
            "/api/v1/search", json={"text": "a dog outdoors", "mode": "text", "top_k": 3}
        )
        agent = await client.post(
            "/api/v1/search/agent", json={"query": "a dog outdoors", "top_k": 3}
        )
        assert direct.status_code == agent.status_code == 200
        assert [r["image_id"] for r in direct.json()["results"]] == [
            r["image_id"] for r in agent.json()["results"]
        ]
        assert agent.json()["planner_attempts"] == 0 and agent.json()["tool_calls"] == 1
        missing = await client.post(
            "/api/v1/search/agent",
            json={"query": "Find landmarks in the city where Hoan Kiem Lake is located"},
        )
        assert (
            missing.json()["status"] == "insufficient_evidence" and missing.json()["results"] == []
        )
        explained = await client.post(
            "/api/v1/search/agent",
            json={"query": "a dog outdoors", "top_k": 1, "include_explanation": True},
        )
        value = explained.json()
        assert explained.status_code == 200 and value["results"]
        assert value["rag"] and value["rag"]["generated"], value.get("warnings")
        assert all(
            c["image_id"] in {i["image_id"] for i in value["results"]}
            for c in value["rag"]["citations"]
        )
