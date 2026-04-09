package com.iflytek.skillhub.dto.internal;

import java.math.BigDecimal;

public record SkillGovernanceSignalResponse(
        String signalType,
        Long skillId,
        String namespace,
        String slug,
        String displayName,
        BigDecimal trustScore,
        BigDecimal qualityScore,
        BigDecimal feedbackScore,
        BigDecimal successRate30d,
        Long downloadCount30d,
        String recommendedAction
) {
}
