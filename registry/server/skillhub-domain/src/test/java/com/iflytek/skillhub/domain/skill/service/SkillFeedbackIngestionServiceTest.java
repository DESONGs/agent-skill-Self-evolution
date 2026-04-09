package com.iflytek.skillhub.domain.skill.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.feedback.SkillRunFeedback;
import com.iflytek.skillhub.domain.feedback.SkillRunFeedbackRepository;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVersionRepository;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class SkillFeedbackIngestionServiceTest {

    @Test
    void ingest_shouldCreateAppendOnlyFeedbackAndResolveSkillFromVersion() {
        SkillRunFeedbackRepository feedbackRepository = org.mockito.Mockito.mock(SkillRunFeedbackRepository.class);
        SkillVersionRepository versionRepository = org.mockito.Mockito.mock(SkillVersionRepository.class);
        SkillVersion version = new SkillVersion(7L, "1.0.0", "owner-1");

        when(feedbackRepository.findByDedupeKey("fb-1")).thenReturn(Optional.empty());
        when(versionRepository.findById(10L)).thenReturn(Optional.of(version));
        when(feedbackRepository.save(any(SkillRunFeedback.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillFeedbackIngestionService service = new SkillFeedbackIngestionService(
                feedbackRepository,
                versionRepository,
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );

        SkillFeedbackIngestionService.IngestionResult result = service.ingest(
                "fb-1",
                "DOWNLOAD",
                "SKILL_VERSION",
                null,
                10L,
                null,
                null,
                null,
                null,
                "DOWNLOAD",
                true,
                null,
                null,
                null,
                "{}",
                null,
                "svc-1"
        );

        assertThat(result.created()).isTrue();
        assertThat(result.feedback().getSkillId()).isEqualTo(7L);
        assertThat(result.feedback().getObservedAt()).isEqualTo(Instant.parse("2026-04-03T00:00:00Z"));
        verify(feedbackRepository).save(any(SkillRunFeedback.class));
    }

    @Test
    void ingest_shouldReturnExistingFeedbackWhenDedupeKeyAlreadyExists() {
        SkillRunFeedbackRepository feedbackRepository = org.mockito.Mockito.mock(SkillRunFeedbackRepository.class);
        SkillVersionRepository versionRepository = org.mockito.Mockito.mock(SkillVersionRepository.class);
        SkillRunFeedback existing = new SkillRunFeedback(
                "fb-1",
                "DOWNLOAD",
                "SKILL_VERSION",
                7L,
                10L,
                null,
                null,
                null,
                null,
                "DOWNLOAD",
                true,
                null,
                null,
                null,
                "{}",
                Instant.parse("2026-04-02T00:00:00Z"),
                "svc-1"
        );

        when(feedbackRepository.findByDedupeKey("fb-1")).thenReturn(Optional.of(existing));

        SkillFeedbackIngestionService service = new SkillFeedbackIngestionService(
                feedbackRepository,
                versionRepository,
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );

        SkillFeedbackIngestionService.IngestionResult result = service.ingest(
                "fb-1",
                "DOWNLOAD",
                "SKILL_VERSION",
                7L,
                10L,
                null,
                null,
                null,
                null,
                "DOWNLOAD",
                true,
                null,
                null,
                null,
                "{}",
                null,
                "svc-1"
        );

        assertThat(result.created()).isFalse();
        assertThat(result.feedback()).isSameAs(existing);
    }

    @Test
    void ingest_shouldRejectSkillVersionMismatch() {
        SkillRunFeedbackRepository feedbackRepository = org.mockito.Mockito.mock(SkillRunFeedbackRepository.class);
        SkillVersionRepository versionRepository = org.mockito.Mockito.mock(SkillVersionRepository.class);
        SkillVersion version = new SkillVersion(7L, "1.0.0", "owner-1");

        when(feedbackRepository.findByDedupeKey("fb-1")).thenReturn(Optional.empty());
        when(versionRepository.findById(10L)).thenReturn(Optional.of(version));

        SkillFeedbackIngestionService service = new SkillFeedbackIngestionService(
                feedbackRepository,
                versionRepository,
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );

        assertThatThrownBy(() -> service.ingest(
                "fb-1",
                "DOWNLOAD",
                "SKILL_VERSION",
                9L,
                10L,
                null,
                null,
                null,
                null,
                "DOWNLOAD",
                true,
                null,
                null,
                null,
                "{}",
                null,
                "svc-1"
        )).isInstanceOf(DomainBadRequestException.class);
    }
}
