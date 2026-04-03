package com.iflytek.skillhub.dto.internal;

import com.fasterxml.jackson.databind.JsonNode;

public record SkillCandidateRequest(
        String candidateKey,
        String candidateSlug,
        String sourceKind,
        JsonNode candidateSpec,
        JsonNode sourceRefs,
        String problemStatement,
        String targetUser,
        String skillBoundary,
        String triggerDescription,
        JsonNode antiTriggers,
        String defaultActionId,
        JsonNode governance,
        JsonNode metrics,
        String generatedBundleKey,
        String generatedManifestKey,
        String reportIndexKey,
        String latestLabRunId,
        String promotionState,
        Long sourceSkillId,
        Long sourceVersionId,
        String actorId
) {}
