package com.iflytek.skillhub.dto.internal;

import java.time.Instant;

public record SkillCandidateSummaryResponse(
        Long id,
        String candidateKey,
        String candidateSlug,
        String sourceKind,
        String problemStatement,
        String targetUser,
        String promotionState,
        Long publishedSkillId,
        Long publishedVersionId,
        String createdBy,
        Instant createdAt,
        Instant updatedAt
) {
}
