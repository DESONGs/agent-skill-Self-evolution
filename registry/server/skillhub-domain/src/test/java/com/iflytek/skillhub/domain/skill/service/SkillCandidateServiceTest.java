package com.iflytek.skillhub.domain.skill.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class SkillCandidateServiceTest {

    @Test
    void create_shouldNormalizeKeyAndDefaultState() {
        SkillCandidateRepository repository = mock(SkillCandidateRepository.class);
        when(repository.findByCandidateKey(org.mockito.ArgumentMatchers.anyString())).thenReturn(Optional.empty());
        when(repository.save(org.mockito.ArgumentMatchers.any(SkillCandidate.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        SkillCandidateService service = new SkillCandidateService(repository);
        SkillCandidate candidate = service.create(new SkillCandidateService.CreateCommand(
                null,
                "Candidate One",
                "{}",
                "workflow",
                "[]",
                "Help users summarize logs",
                "operators",
                null,
                null,
                "[]",
                null,
                "{}",
                "{}",
                "candidates/bundle.zip",
                null,
                null,
                null,
                null,
                null,
                null,
                "creator-1"
        ));

        assertThat(candidate.getCandidateKey()).startsWith("candidate-one-");
        assertThat(candidate.getCandidateSlug()).isEqualTo("candidate-one");
        assertThat(candidate.getPromotionState()).isEqualTo("CREATED");
        assertThat(candidate.getSourceKind()).isEqualTo("WORKFLOW");
    }

    @Test
    void create_shouldRejectDuplicateCandidateKey() {
        SkillCandidateRepository repository = mock(SkillCandidateRepository.class);
        SkillCandidate existing = new SkillCandidate(
                "cand-1",
                "cand-1",
                "WORKFLOW",
                "{}",
                "[]",
                null,
                null,
                null,
                null,
                "[]",
                null,
                "{}",
                "{}",
                null,
                null,
                null,
                null,
                "CREATED",
                null,
                null,
                null,
                null,
                "creator-1"
        );
        when(repository.findByCandidateKey("cand-1")).thenReturn(Optional.of(existing));

        SkillCandidateService service = new SkillCandidateService(repository);

        assertThatThrownBy(() -> service.create(new SkillCandidateService.CreateCommand(
                "cand-1",
                "cand-1",
                "{}",
                "WORKFLOW",
                "[]",
                null,
                null,
                null,
                null,
                "[]",
                null,
                "{}",
                "{}",
                null,
                null,
                null,
                null,
                "CREATED",
                null,
                null,
                "creator-1"
        ))).isInstanceOf(DomainBadRequestException.class);
    }

    @Test
    void list_shouldSortByUpdatedAtDescending() {
        SkillCandidateRepository repository = mock(SkillCandidateRepository.class);
        SkillCandidate older = new SkillCandidate(
                "cand-1", "cand-1", "WORKFLOW", "{}", "[]", null, null, null, null, "[]",
                null, "{}", "{}", null, null, null, null, "CREATED", null, null, null, null, "u");
        SkillCandidate newer = new SkillCandidate(
                "cand-2", "cand-2", "WORKFLOW", "{}", "[]", null, null, null, null, "[]",
                null, "{}", "{}", null, null, null, null, "CREATED", null, null, null, null, "u");
        setUpdatedAt(older, java.time.Instant.parse("2026-04-02T00:00:00Z"));
        setUpdatedAt(newer, java.time.Instant.parse("2026-04-03T00:00:00Z"));
        when(repository.findAllByOrderByUpdatedAtDesc()).thenReturn(List.of(older, newer));

        SkillCandidateService service = new SkillCandidateService(repository);

        assertThat(service.list(null)).extracting(SkillCandidate::getCandidateKey)
                .containsExactly("cand-2", "cand-1");
    }

    private void setUpdatedAt(SkillCandidate candidate, java.time.Instant updatedAt) {
        try {
            var field = SkillCandidate.class.getDeclaredField("updatedAt");
            field.setAccessible(true);
            field.set(candidate, updatedAt);
        } catch (ReflectiveOperationException ex) {
            throw new IllegalStateException(ex);
        }
    }
}
