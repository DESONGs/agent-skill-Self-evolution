package com.iflytek.skillhub.domain.feedback;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.security.SecurityAudit;
import com.iflytek.skillhub.domain.security.SecurityAuditRepository;
import com.iflytek.skillhub.domain.security.ScannerType;
import com.iflytek.skillhub.domain.security.SecurityVerdict;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.domain.skill.SkillVersionStats;
import com.iflytek.skillhub.domain.skill.SkillVersionStatsRepository;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.service.SkillLifecycleProjectionService;
import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class SkillScoreSnapshotServiceTest {

    @Mock
    private SkillRunFeedbackRepository skillRunFeedbackRepository;
    @Mock
    private SkillScoreSnapshotRepository skillScoreSnapshotRepository;
    @Mock
    private SkillRepository skillRepository;
    @Mock
    private SkillVersionStatsRepository skillVersionStatsRepository;
    @Mock
    private SkillLifecycleProjectionService skillLifecycleProjectionService;
    @Mock
    private SecurityAuditRepository securityAuditRepository;

    private SkillScoreSnapshotService service;

    @BeforeEach
    void setUp() {
        service = new SkillScoreSnapshotService(
                skillRunFeedbackRepository,
                skillScoreSnapshotRepository,
                skillRepository,
                skillVersionStatsRepository,
                skillLifecycleProjectionService,
                securityAuditRepository,
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );
    }

    @Test
    void refreshSkillSnapshot_shouldAggregateThirtyDayFeedback() throws Exception {
        Skill skill = new Skill(10L, "demo", "owner-1", SkillVisibility.PUBLIC);
        setField(skill, "id", 1L);

        SecurityAudit audit = new SecurityAudit(101L, ScannerType.SKILL_SCANNER);
        audit.setVerdict(SecurityVerdict.SAFE);
        audit.setScannedAt(Instant.parse("2026-04-01T00:00:00Z"));

        SkillRunFeedback download = new SkillRunFeedback(
                "download-1", "DOWNLOAD", "SKILL_VERSION", 1L, 101L, null, null, null,
                null, "DOWNLOAD", true, null, null, null, "{}", Instant.parse("2026-04-02T00:00:00Z"), "actor"
        );
        SkillRunFeedback success = new SkillRunFeedback(
                "success-1", "RUNTIME", "SKILL_VERSION", 1L, 101L, null, null, null,
                null, "EXECUTION", true, 5, 100L, null, "{}", Instant.parse("2026-04-02T01:00:00Z"), "actor"
        );
        SkillRunFeedback failure = new SkillRunFeedback(
                "failure-1", "RUNTIME", "SKILL_VERSION", 1L, 101L, null, null, null,
                null, "EXECUTION", false, null, 120L, "E_TIMEOUT", "{}", Instant.parse("2026-04-02T02:00:00Z"), "actor"
        );

        when(skillRepository.findById(1L)).thenReturn(Optional.of(skill));
        when(skillLifecycleProjectionService.projectPublishedSummaries(List.of(skill))).thenReturn(Map.of(
                1L,
                new SkillLifecycleProjectionService.Projection(
                        new SkillLifecycleProjectionService.VersionProjection(101L, "1.2.0", "PUBLISHED"),
                        new SkillLifecycleProjectionService.VersionProjection(101L, "1.2.0", "PUBLISHED"),
                        null,
                        SkillLifecycleProjectionService.ResolutionMode.PUBLISHED
                )
        ));
        when(skillRunFeedbackRepository.findBySkillIdAndObservedAtGreaterThanEqual(any(), any()))
                .thenReturn(List.of(download, success, failure));
        when(securityAuditRepository.findLatestActiveByVersionId(101L)).thenReturn(List.of(audit));
        when(skillScoreSnapshotRepository.findBySkillId(1L)).thenReturn(Optional.empty());
        when(skillScoreSnapshotRepository.save(any(SkillScoreSnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillScoreSnapshot snapshot = service.refreshSkillSnapshot(1L);

        assertEquals(101L, snapshot.getLatestPublishedVersionId());
        assertEquals(1L, snapshot.getDownloadCount30d());
        assertEquals(new BigDecimal("0.5000"), snapshot.getSuccessRate30d());
        assertEquals(new BigDecimal("0.6250"), snapshot.getRatingBayes());
        assertEquals(new BigDecimal("0.6250"), snapshot.getFeedbackScore());
        assertEquals(new BigDecimal("0.5500"), snapshot.getQualityScore());
        assertEquals(new BigDecimal("0.6750"), snapshot.getTrustScore());
        verify(skillScoreSnapshotRepository).save(any(SkillScoreSnapshot.class));
    }

    @Test
    void bootstrapMissingSnapshots_shouldSeedDownloadCountFromExistingCounters() throws Exception {
        Skill skill = new Skill(10L, "demo", "owner-1", SkillVisibility.PUBLIC);
        setField(skill, "id", 1L);
        setField(skill, "downloadCount", 8L);

        SecurityAudit audit = new SecurityAudit(101L, ScannerType.SKILL_SCANNER);
        audit.setVerdict(SecurityVerdict.SAFE);
        audit.setScannedAt(Instant.parse("2026-03-01T00:00:00Z"));

        SkillVersionStats stats = new SkillVersionStats(101L, 1L);
        setField(stats, "downloadCount", 12L);

        when(skillRepository.findAll()).thenReturn(List.of(skill));
        when(skillLifecycleProjectionService.projectPublishedSummaries(List.of(skill))).thenReturn(Map.of(
                1L,
                new SkillLifecycleProjectionService.Projection(
                        new SkillLifecycleProjectionService.VersionProjection(101L, "1.0.0", "PUBLISHED"),
                        new SkillLifecycleProjectionService.VersionProjection(101L, "1.0.0", "PUBLISHED"),
                        null,
                        SkillLifecycleProjectionService.ResolutionMode.PUBLISHED
                )
        ));
        when(skillScoreSnapshotRepository.findBySkillId(1L)).thenReturn(Optional.empty());
        when(skillVersionStatsRepository.findBySkillVersionId(101L)).thenReturn(Optional.of(stats));
        when(securityAuditRepository.findLatestActiveByVersionId(101L)).thenReturn(List.of(audit));
        when(skillScoreSnapshotRepository.save(any(SkillScoreSnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillScoreSnapshotService.SnapshotRefreshResult result = service.bootstrapMissingSnapshotsDetailed();

        assertEquals(1, result.refreshedCount());
        assertEquals(List.of(1L), result.skillIds());
        verify(skillScoreSnapshotRepository).save(any(SkillScoreSnapshot.class));
    }

    private void setField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }
}
