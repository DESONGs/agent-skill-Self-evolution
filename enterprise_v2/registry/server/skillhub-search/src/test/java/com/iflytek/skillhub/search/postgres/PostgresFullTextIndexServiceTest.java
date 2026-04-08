package com.iflytek.skillhub.search.postgres;

import com.iflytek.skillhub.infra.jpa.SkillSearchDocumentEntity;
import com.iflytek.skillhub.infra.jpa.SkillSearchDocumentJpaRepository;
import com.iflytek.skillhub.search.HashingSearchEmbeddingService;
import com.iflytek.skillhub.search.SkillSearchDocument;
import java.math.BigDecimal;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class PostgresFullTextIndexServiceTest {

    @Test
    void indexShouldTruncateOnlyColumnsThatStillHaveDatabaseLimitsAndPersistExpandedFields() {
        SkillSearchDocumentJpaRepository repository = mock(SkillSearchDocumentJpaRepository.class);
        when(repository.findBySkillId(1L)).thenReturn(Optional.empty());

        PostgresFullTextIndexService service = new PostgresFullTextIndexService(
                repository,
                new HashingSearchEmbeddingService()
        );

        SkillSearchDocument document = new SkillSearchDocument(
                1L,
                2L,
                "n".repeat(80),
                "o".repeat(140),
                "t".repeat(300),
                "summary",
                "k".repeat(700),
                "search text",
                null,
                "PUBLIC",
                "ACTIVE",
                99L,
                "1.2.3",
                Instant.parse("2026-04-03T10:15:30Z"),
                "[\"guide\",\"official\"]",
                "[\"runtime:python\",\"profile:default\"]",
                "[\"node\",\"uv\"]",
                "[\"tooling\",\"action\"]",
                new BigDecimal("0.8100"),
                new BigDecimal("0.7500"),
                new BigDecimal("0.6400"),
                new BigDecimal("0.9200"),
                "SAFE",
                "PUBLISHED"
        );

        service.index(document);

        ArgumentCaptor<SkillSearchDocumentEntity> captor = ArgumentCaptor.forClass(SkillSearchDocumentEntity.class);
        verify(repository).save(captor.capture());

        SkillSearchDocumentEntity entity = captor.getValue();
        assertThat(entity.getNamespaceSlug()).hasSize(64);
        assertThat(entity.getOwnerId()).hasSize(128);
        assertThat(entity.getTitle()).hasSize(300);
        assertThat(entity.getKeywords()).hasSize(700);
        assertThat(entity.getSearchText()).isEqualTo("search text");
        assertThat(entity.getLatestPublishedVersionId()).isEqualTo(99L);
        assertThat(entity.getLatestPublishedVersion()).isEqualTo("1.2.3");
        assertThat(entity.getPublishedAt()).isEqualTo(Instant.parse("2026-04-03T10:15:30Z"));
        assertThat(entity.getLabelSlugs()).contains("guide");
        assertThat(entity.getRuntimeTags()).contains("runtime:python");
        assertThat(entity.getToolTags()).contains("node");
        assertThat(entity.getActionKinds()).contains("tooling");
        assertThat(entity.getTrustScore()).isEqualByComparingTo(new BigDecimal("0.8100"));
        assertThat(entity.getQualityScore()).isEqualByComparingTo(new BigDecimal("0.7500"));
        assertThat(entity.getFeedbackScore()).isEqualByComparingTo(new BigDecimal("0.6400"));
        assertThat(entity.getSuccessRate30d()).isEqualByComparingTo(new BigDecimal("0.9200"));
        assertThat(entity.getScanVerdict()).isEqualTo("SAFE");
        assertThat(entity.getReviewState()).isEqualTo("PUBLISHED");
    }
}
