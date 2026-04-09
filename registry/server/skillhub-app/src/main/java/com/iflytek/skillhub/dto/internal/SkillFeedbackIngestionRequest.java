package com.iflytek.skillhub.dto.internal;

import java.time.Instant;

public record SkillFeedbackIngestionRequest(
        String dedupeKey,
        String feedbackSource,
        String subjectType,
        Long skillId,
        Long skillVersionId,
        Long skillActionId,
        Long skillCandidateId,
        Long environmentProfileId,
        String sourceRunId,
        String feedbackType,
        Boolean success,
        Integer rating,
        Long latencyMs,
        String errorCode,
        String payloadJson,
        Instant observedAt,
        String actorId
) {}
