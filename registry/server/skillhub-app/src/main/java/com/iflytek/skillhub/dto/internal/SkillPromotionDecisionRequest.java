package com.iflytek.skillhub.dto.internal;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;

public record SkillPromotionDecisionRequest(
        String decision,
        String decisionMode,
        JsonNode reasons,
        JsonNode scores,
        String evidenceIndexKey,
        String decidedBy,
        Instant decidedAt
) {}
