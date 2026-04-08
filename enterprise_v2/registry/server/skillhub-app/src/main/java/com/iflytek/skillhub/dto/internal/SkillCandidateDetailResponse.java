package com.iflytek.skillhub.dto.internal;

import java.time.Instant;
import java.util.List;

public record SkillCandidateDetailResponse(
        Long id,
        String candidateKey,
        String candidateSlug,
        String candidateSpecJson,
        String sourceKind,
        String sourceRefsJson,
        String problemStatement,
        String targetUser,
        String skillBoundary,
        String triggerDescription,
        String antiTriggersJson,
        String defaultActionId,
        String governanceJson,
        String metricsJson,
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
        Instant updatedAt,
        List<SkillPromotionDecisionResponse> decisions
) {
}
