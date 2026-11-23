"""Adapters only: image retrieval/validation/reranking/RAG stay in existing services."""

from time import perf_counter

from app.schemas.agent import ToolOutput
from app.schemas.rag import RagImage, RagRequest
from app.schemas.search import SearchRequest
from app.services.agent.errors import AgentError
from app.services.rag.evidence_retriever import EvidenceRetriever
from app.services.rag.generator import Generator
from app.services.rag.rag_service import RagService
from app.services.search.search_service import SearchService


class AgentTools:
    def __init__(self, services, runtime, generator, knowledge):
        self.services, self.runtime, self.generator, self.knowledge = (
            services,
            runtime,
            generator,
            knowledge,
        )

    def require_runtime(self):
        if not self.runtime or not self.runtime.available:
            raise AgentError("SEARCH_UNAVAILABLE")

    async def invoke(self, name, args, state, emit):
        values = args.model_dump()
        if name == "entity_lookup":
            return await self.knowledge.lookup(**values)
        if name in {"relationship_lookup", "get_related_entities"}:
            return await self.knowledge.relationships(**values)
        self.require_runtime()
        if name == "metadata_search":
            ids = await self.knowledge.metadata_ids(
                args.filters, self.runtime.registry.index.id, args.top_k
            )
            _, images, _ = await EvidenceRetriever(self.runtime).retrieve(ids)
            return ToolOutput(
                images=images, image_ids=[i.image_id for i in images], insufficient=not images
            )
        if name == "retrieve_image_details":
            _, images, _ = await EvidenceRetriever(self.runtime).retrieve(args.image_ids)
            return ToolOutput(
                images=images, image_ids=[i.image_id for i in images], insufficient=not images
            )
        if name == "rag_explain":
            if not self.services.settings.agent_rag_enabled:
                raise AgentError("AGENT_RAG_DISABLED")
            generator = self.generator
            temporary = None
            cap = state.request.budgets.max_output_tokens
            if cap < generator.settings.rag_max_output_tokens:
                temporary = Generator(
                    generator.settings.model_copy(update={"rag_max_output_tokens": cap})
                )
                generator = temporary
            try:
                request = RagRequest(
                    image_ids=args.image_ids,
                    question=state.request.query,
                    language=state.request.language,
                    expected_index_id=self.runtime.registry.index.id,
                    context_format="compact",
                )
                rag_started = (perf_counter() - state.started_at) * 1000
                response = await RagService(self.runtime, generator).execute(
                    request, state.request_id, emit
                )
                return ToolOutput(
                    image_ids=[i.image_id for i in response.results],
                    images=response.results,
                    rag=response.rag,
                    timing={**response.latency, "agent_rag_started_ms": rag_started},
                    warnings=[response.rag.error_code] if response.rag.error_code else [],
                )
            finally:
                if temporary:
                    await temporary.close()
        associations = []
        filters = args.filters.model_copy(deep=True)
        if args.entity_ids is not None:
            associations = await self.knowledge.associations(args.entity_ids)
            ids = sorted({a.image_id for a in associations}, key=str)
            if not ids:
                return ToolOutput(insufficient=True, warnings=["NO_VERIFIED_IMAGE_ASSOCIATIONS"])
            filters.image_ids = (
                ids if filters.image_ids is None else [i for i in ids if i in filters.image_ids]
            )
        if args.image_ids is not None:
            filters.image_ids = (
                list(args.image_ids)
                if filters.image_ids is None
                else [i for i in args.image_ids if i in filters.image_ids]
            )
        if filters.image_ids is not None and not filters.image_ids:
            return ToolOutput(insufficient=True)
        if name == "multimodal_image_search" and not args.image_id:
            raise AgentError("IMAGE_REFERENCE_REQUIRED")
        request = SearchRequest(
            text=args.query,
            image_id=args.image_id,
            mode=args.mode,
            top_k=min(args.top_k, state.request.top_k),
            filters=filters,
            rerank={"enabled": name == "rerank_images" or args.rerank},
        )
        result = await SearchService(self.runtime).execute(request, state.request_id)
        images = [RagImage.model_validate(i.model_dump()) for i in result.results]
        return ToolOutput(
            images=images,
            image_ids=[i.image_id for i in images],
            associations=associations,
            insufficient=not images,
            timing=result.latency,
        )
