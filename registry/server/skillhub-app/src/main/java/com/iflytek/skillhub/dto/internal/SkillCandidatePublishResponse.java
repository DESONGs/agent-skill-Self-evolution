package com.iflytek.skillhub.dto.internal;

public record SkillCandidatePublishResponse(
        Long candidateId,
        String promotionState,
        Long publishedSkillId,
        Long publishedVersionId,
        String namespace,
        String slug,
        String version,
        String status
) {
}
