package com.iflytek.skillhub.dto.internal;

public record SkillGovernanceSignalSummaryResponse(
        long lowSuccessRateCount,
        long lowFeedbackScoreCount,
        long highImpactRiskCount,
        long candidatePromotionPendingCount,
        long candidateRejectedCount
) {}
