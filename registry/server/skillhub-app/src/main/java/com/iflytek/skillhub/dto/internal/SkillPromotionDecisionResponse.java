package com.iflytek.skillhub.dto.internal;

import java.time.Instant;

public record SkillPromotionDecisionResponse(
        Long id,
        Long skillCandidateId,
        String decision,
        String decisionMode,
        String reasonsJson,
        String scoresJson,
        String evidenceIndexKey,
        String decidedBy,
        Instant decidedAt,
        Instant createdAt
) {
}
