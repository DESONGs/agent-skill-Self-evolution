package com.iflytek.skillhub.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record SkillSummaryResponse(
        Long id,
        String slug,
        String displayName,
        String summary,
        String status,
        Long downloadCount,
        Integer starCount,
        BigDecimal ratingAvg,
        Integer ratingCount,
        String namespace,
        Instant updatedAt,
        boolean canSubmitPromotion,
        SkillLifecycleVersionResponse headlineVersion,
        SkillLifecycleVersionResponse publishedVersion,
        SkillLifecycleVersionResponse ownerPreviewVersion,
        String resolutionMode,
        List<String> labels,
        List<String> runtimeTags,
        List<String> actionKinds,
        BigDecimal successRate,
        BigDecimal trustScore
) {
    public SkillSummaryResponse(
            Long id,
            String slug,
            String displayName,
            String summary,
            String status,
            Long downloadCount,
            Integer starCount,
            BigDecimal ratingAvg,
            Integer ratingCount,
            String namespace,
            Instant updatedAt,
            boolean canSubmitPromotion,
            SkillLifecycleVersionResponse headlineVersion,
            SkillLifecycleVersionResponse publishedVersion,
            SkillLifecycleVersionResponse ownerPreviewVersion,
            String resolutionMode) {
        this(
                id,
                slug,
                displayName,
                summary,
                status,
                downloadCount,
                starCount,
                ratingAvg,
                ratingCount,
                namespace,
                updatedAt,
                canSubmitPromotion,
                headlineVersion,
                publishedVersion,
                ownerPreviewVersion,
                resolutionMode,
                List.of(),
                List.of(),
                List.of(),
                null,
                null
        );
    }
}
