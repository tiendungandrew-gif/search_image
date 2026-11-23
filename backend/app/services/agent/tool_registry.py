from dataclasses import dataclass
from uuid import UUID

from pydantic import Field

from app.schemas.agent import EntityType, IdInput, Predicate, StrictModel, ToolOutput
from app.schemas.filters import Filters


class EntityLookupArgs(StrictModel):
    name: str = Field(min_length=1, max_length=256)
    entity_type: EntityType | None = None


class RelationshipArgs(StrictModel):
    entity_ids: IdInput
    predicate: Predicate
    direction: str = Field(default="out", pattern=r"^(out|in)$")
    entity_type: EntityType | None = None
    limit: int = Field(default=50, ge=1, le=50)


class SearchArgs(StrictModel):
    query: str | None = Field(default=None, min_length=1, max_length=2000)
    entity_ids: IdInput | None = None
    image_ids: IdInput | None = None
    image_id: UUID | None = None
    filters: Filters = Field(default_factory=Filters)
    mode: str = Field(default="text", pattern=r"^(text|multi_intent|multimodal|image)$")
    top_k: int = Field(default=10, ge=1, le=50)
    rerank: bool = False


class MetadataArgs(StrictModel):
    filters: Filters
    top_k: int = Field(default=10, ge=1, le=50)


class ImageIdsArgs(StrictModel):
    image_ids: IdInput


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type
    capability: str
    hop_cost: int
    max_results: int = 50
    permission: str = "search:read"

    def public(self, settings):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": ToolOutput.model_json_schema(),
            "timeout_seconds": settings.rag_request_timeout_seconds
            if self.capability == "rag"
            else settings.agent_tool_timeout_seconds,
            "required_capability": self.capability,
            "permission": self.permission,
            "max_results": self.max_results,
            "errors": ["TOOL_TIMEOUT", "INSUFFICIENT_EVIDENCE", "DEPENDENCY_UNAVAILABLE"],
        }


def build_registry():
    definitions = [
        ToolDefinition(
            "semantic_image_search",
            "Search indexed images; entity IDs enforce verified image associations.",
            SearchArgs,
            "search",
            1,
        ),
        ToolDefinition(
            "multimodal_image_search",
            "Reuse paired text/stored-image retrieval.",
            SearchArgs,
            "search",
            1,
        ),
        ToolDefinition(
            "metadata_search",
            "Filter current indexed image metadata; no invented semantic scores.",
            MetadataArgs,
            "search",
            1,
        ),
        ToolDefinition(
            "entity_lookup",
            "Resolve one stored canonical name or explicit alias.",
            EntityLookupArgs,
            "knowledge",
            0,
        ),
        ToolDefinition(
            "relationship_lookup",
            "Traverse source-attributed verified relationships.",
            RelationshipArgs,
            "knowledge",
            1,
        ),
        ToolDefinition(
            "get_related_entities",
            "Get verified related entities in the declared direction.",
            RelationshipArgs,
            "knowledge",
            1,
        ),
        ToolDefinition(
            "retrieve_image_details",
            "Revalidate current image objects, vectors and metadata.",
            ImageIdsArgs,
            "search",
            0,
        ),
        ToolDefinition(
            "rerank_images",
            "Reuse the existing bounded reranker for supplied images.",
            SearchArgs,
            "search",
            0,
        ),
        ToolDefinition(
            "rag_explain",
            "Optional existing grounded image-metadata explanation.",
            ImageIdsArgs,
            "rag",
            0,
        ),
    ]
    return {definition.name: definition for definition in definitions}
