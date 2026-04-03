package com.iflytek.skillhub.dto.internal;

import java.math.BigDecimal;
import java.util.List;

public record SkillGovernanceSignalItemResponse(
        Long skillId,
        String slug,
        String displayName,
        Long latestPublishedVersionId,
        String latestPublishedVersion,
        BigDecimal trustScore,
        BigDecimal qualityScore,
        BigDecimal feedbackScore,
        BigDecimal successRate30d,
        Long downloadCount30d,
        BigDecimal labScore,
        List<String> signals,
        List<ErrorCount> topErrors
) {
    public record ErrorCount(
            String errorCode,
            long count
    ) {}
}
