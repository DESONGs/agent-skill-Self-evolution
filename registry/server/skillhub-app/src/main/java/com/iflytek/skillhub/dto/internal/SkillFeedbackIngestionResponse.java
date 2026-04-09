package com.iflytek.skillhub.dto.internal;

import java.time.Instant;

public record SkillFeedbackIngestionResponse(
        Long id,
        String dedupeKey,
        Long skillId,
        Long skillVersionId,
        String feedbackType,
        boolean created,
        Instant observedAt,
        Instant ingestedAt
) {}
