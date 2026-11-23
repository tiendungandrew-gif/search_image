from app.services.agent.errors import AgentError
from app.services.rag.evidence_retriever import EvidenceRetriever


class EvidenceAggregator:
    def __init__(self, runtime, knowledge):
        self.runtime, self.knowledge = runtime, knowledge

    async def aggregate(self, state):
        images, entities, relations, associations, sources = {}, {}, {}, {}, {}
        rag = None
        tool_by_step = {t.step_id: t.tool for t in state.traces}
        for identity, output in state.outputs.items():
            if output.insufficient:
                continue
            for entity in output.entities:
                entities[entity.entity_id] = entity
            for relation in output.relations:
                if not relation.verified:
                    raise AgentError("UNVERIFIED_RELATIONSHIP")
                relations[relation.evidence_id] = relation
            for association in output.associations:
                associations[
                    (association.image_id, association.entity_id, association.relation)
                ] = association
            if tool_by_step[identity] == "rerank_images":
                images = {}
            for image in output.images:
                images.setdefault(image.image_id, image)
                sources.setdefault(str(image.image_id), []).append(
                    identity + ":" + tool_by_step[identity]
                )
            rag = output.rag or rag
        selected = list(images.values())[: state.request.top_k]
        if selected:
            _, selected, excluded = await EvidenceRetriever(self.runtime).retrieve(
                [i.image_id for i in selected], selected
            )
            if excluded:
                state.warnings.append("STALE_IMAGES_EXCLUDED")
        ids = {i.image_id for i in selected}
        links = [a for a in associations.values() if a.image_id in ids]
        if state.require_entity_links:
            targets = (
                set(state.outputs.get("targets").entity_ids)
                if "targets" in state.outputs
                else set()
            )
            links = [a for a in links if a.entity_id in targets and a.verified]
            if ids - {a.image_id for a in links}:
                raise AgentError("MISSING_VERIFIED_IMAGE_ASSOCIATION", "insufficient_evidence")
        if not await self.knowledge.validate_evidence(
            list(entities.values()), list(relations.values()), links
        ):
            raise AgentError("INVALID_KNOWLEDGE_EVIDENCE", "insufficient_evidence")
        if rag and any(c.image_id not in ids for c in rag.citations):
            rag = None
            state.warnings.append("STALE_RAG_CITATION_EXCLUDED")
        return (
            selected,
            list(entities.values()),
            list(relations.values()),
            links,
            rag,
            {k: v for k, v in sources.items() if k in {str(i) for i in ids}},
        )
