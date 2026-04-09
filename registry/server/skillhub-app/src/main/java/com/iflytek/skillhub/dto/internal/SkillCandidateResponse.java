package com.iflytek.skillhub.dto.internal;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;

public record SkillCandidateResponse(
        Long id,
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
        Long publishedSkillId,
        Long publishedVersionId,
        String createdBy,
        Instant createdAt,
        Instant updatedAt
) {}
