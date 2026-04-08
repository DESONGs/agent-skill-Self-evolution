package com.iflytek.skillhub.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshot;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotRepository;
import com.iflytek.skillhub.domain.namespace.Namespace;
import com.iflytek.skillhub.domain.namespace.NamespaceRepository;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalsResponse;
import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class SkillGovernanceSignalAppServiceTest {

    @Test
    void listSkillSignals_shouldBuildSummaryAndItemQueues() {
        SkillScoreSnapshotRepository snapshotRepository = mock(SkillScoreSnapshotRepository.class);
        SkillRepository skillRepository = mock(SkillRepository.class);
        NamespaceRepository namespaceRepository = mock(NamespaceRepository.class);
        SkillCandidateRepository candidateRepository = mock(SkillCandidateRepository.class);

        SkillScoreSnapshot snapshot = new SkillScoreSnapshot(1L);
        snapshot.setTrustScore(new BigDecimal("0.4200"));
        snapshot.setQualityScore(new BigDecimal("0.5100"));
        snapshot.setFeedbackScore(new BigDecimal("0.4100"));
        snapshot.setSuccessRate30d(new BigDecimal("0.3800"));
        snapshot.setDownloadCount30d(99L);

        Skill skill = new Skill(7L, "demo", "owner-1", SkillVisibility.PUBLIC);
        setField(skill, "id", 1L);
        skill.setDisplayName("Demo");

        Namespace namespace = new Namespace("team-a", "Team A", "owner-1");
        setField(namespace, "id", 7L);

        when(snapshotRepository.findAllByOrderByUpdatedAtDesc()).thenReturn(List.of(snapshot));
        when(skillRepository.findByIdIn(List.of(1L))).thenReturn(List.of(skill));
        when(namespaceRepository.findByIdIn(List.of(7L))).thenReturn(List.of(namespace));
        when(candidateRepository.findByPromotionState("PROMOTION_PENDING")).thenReturn(List.of());
        when(candidateRepository.findByPromotionState("REJECTED")).thenReturn(List.of());

        SkillGovernanceSignalAppService service = new SkillGovernanceSignalAppService(
                snapshotRepository,
                skillRepository,
                namespaceRepository,
                candidateRepository
        );

        SkillGovernanceSignalsResponse response = service.listSkillSignals(10);

        assertThat(response.summary().lowSuccessRateCount()).isEqualTo(1);
        assertThat(response.summary().lowFeedbackScoreCount()).isEqualTo(1);
        assertThat(response.summary().highImpactRiskCount()).isEqualTo(1);
        assertThat(response.items()).hasSize(2);
        assertThat(response.items().get(0).slug()).isEqualTo("demo");
    }

    private void setField(Object target, String fieldName, Object value) {
        try {
            Field field = target.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException ex) {
            throw new IllegalStateException(ex);
        }
    }
}
