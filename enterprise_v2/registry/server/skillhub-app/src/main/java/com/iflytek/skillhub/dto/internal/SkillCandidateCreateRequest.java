package com.iflytek.skillhub.dto.internal;

public record SkillCandidateCreateRequest(
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
        String createdBy
) {
}
