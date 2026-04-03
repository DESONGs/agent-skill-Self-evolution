package com.iflytek.skillhub.dto;

import java.time.Instant;

public record PromotionResponseDto(
        Long id,
        Long sourceSkillId,
        String sourceNamespace,
        String sourceSkillSlug,
        String sourceVersion,
        String targetNamespace,
        Long targetSkillId,
        String status,
        String submittedBy,
        String submittedByName,
        String reviewedBy,
        String reviewedByName,
        String reviewComment,
        Instant submittedAt,
        Instant reviewedAt
) {}
