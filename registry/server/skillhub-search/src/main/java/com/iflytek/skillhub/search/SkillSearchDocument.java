package com.iflytek.skillhub.search;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Denormalized search document model written to and read from the search subsystem.
 */
public record SkillSearchDocument(
        Long skillId,
        Long namespaceId,
        String namespaceSlug,
        String ownerId,
        String title,
        String summary,
        String keywords,
        String searchText,
        String semanticVector,
        String visibility,
        String status,
        Long latestPublishedVersionId,
        String latestPublishedVersion,
        Instant publishedAt,
        String labelSlugs,
        String runtimeTags,
        String toolTags,
        String actionKinds,
        BigDecimal trustScore,
        BigDecimal qualityScore,
        BigDecimal feedbackScore,
        BigDecimal successRate30d,
        String scanVerdict,
        String reviewState
) {
    private static final BigDecimal NEUTRAL_SCORE = new BigDecimal("0.5000");

    public SkillSearchDocument(
            Long skillId,
            Long namespaceId,
            String namespaceSlug,
            String ownerId,
            String title,
            String summary,
            String keywords,
            String searchText,
            String semanticVector,
            String visibility,
            String status) {
        this(
                skillId,
                namespaceId,
                namespaceSlug,
                ownerId,
                title,
                summary,
                keywords,
                searchText,
                semanticVector,
                visibility,
                status,
                null,
                null,
                null,
                "[]",
                "[]",
                "[]",
                "[]",
                NEUTRAL_SCORE,
                NEUTRAL_SCORE,
                NEUTRAL_SCORE,
                NEUTRAL_SCORE,
                "UNKNOWN",
                "UNKNOWN"
        );
    }
}
