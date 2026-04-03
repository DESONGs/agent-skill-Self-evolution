package com.iflytek.skillhub.dto.internal;

import java.time.Instant;

public record SkillPromotionDecisionCreateRequest(
        String decision,
        String decisionMode,
        String reasonsJson,
        String scoresJson,
        String evidenceIndexKey,
        String decidedBy,
        Instant decidedAt
) {
}
