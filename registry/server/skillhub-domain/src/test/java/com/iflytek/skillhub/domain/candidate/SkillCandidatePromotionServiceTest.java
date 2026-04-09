package com.iflytek.skillhub.domain.candidate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.service.SkillPublishService;
import com.iflytek.skillhub.domain.skill.validation.PackageEntry;
import java.lang.reflect.Field;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class SkillCandidatePromotionServiceTest {

    @Mock
    private SkillCandidateService skillCandidateService;
    @Mock
    private SkillPromotionDecisionService skillPromotionDecisionService;
    @Mock
    private SkillPublishService skillPublishService;
    @Mock
    private SkillScoreSnapshotService skillScoreSnapshotService;

    private SkillCandidatePromotionService service;

    @BeforeEach
    void setUp() {
        service = new SkillCandidatePromotionService(
                skillCandidateService,
                skillPromotionDecisionService,
                skillPublishService,
                skillScoreSnapshotService,
                new ObjectMapper(),
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );
    }

    @Test
    void publishCandidate_shouldParsePackageEntriesAndMarkCandidatePublished() throws Exception {
        String specJson = """
                {
                  "packageEntries": [
                    {"path":"SKILL.md","content":"IyBEZW1vIFNraWxs","encoding":"BASE64","contentType":"text/markdown"}
                  ]
                }
                """;
        SkillCandidate candidate = new SkillCandidate(
                "cand-1", "candidate-one", "WORKFLOW", specJson, "[]", null, null, null, null,
                "[]", null, "{}", "{}", null, null, null, null, "PROMOTION_PENDING", null, null, null, null, "svc-1"
        );
        setField(candidate, "id", 1L);
        SkillPromotionDecision decision = new SkillPromotionDecision(
                1L, "PROMOTE", "HUMAN_REVIEW", "[\"good\"]", "{\"overall\":0.9}", null, "reviewer-1",
                Instant.parse("2026-04-03T00:10:00Z")
        );
        SkillVersion publishedVersion = new SkillVersion(10L, "1.0.0", "svc-1");
        setField(publishedVersion, "id", 101L);

        SkillCandidate publishedCandidate = new SkillCandidate(
                "cand-1", "candidate-one", "WORKFLOW", specJson, "[]", null, null, null, null,
                "[]", null, "{}", "{}", null, null, null, null, "PUBLISHED", null, null, 10L, 101L, "svc-1"
        );
        setField(publishedCandidate, "id", 1L);

        when(skillCandidateService.getCandidate(1L)).thenReturn(candidate);
        when(skillPromotionDecisionService.latestDecision(1L)).thenReturn(java.util.Optional.of(decision));
        when(skillPublishService.publishFromEntries(eq("team-a"), any(), eq("publisher-1"), eq(SkillVisibility.PUBLIC), eq(Set.of("SUPER_ADMIN"))))
                .thenReturn(new SkillPublishService.PublishResult(10L, "demo-skill", publishedVersion));
        when(skillCandidateService.markPublished(1L, 10L, 101L)).thenReturn(publishedCandidate);

        SkillCandidatePromotionService.CandidatePublishResult result = service.publishCandidate(
                1L,
                new SkillCandidatePromotionService.PublishCommand("team-a", "publisher-1", SkillVisibility.PUBLIC, Set.of("SUPER_ADMIN"))
        );

        ArgumentCaptor<List<PackageEntry>> entriesCaptor = ArgumentCaptor.forClass(List.class);
        verify(skillPublishService).publishFromEntries(eq("team-a"), entriesCaptor.capture(), eq("publisher-1"), eq(SkillVisibility.PUBLIC), eq(Set.of("SUPER_ADMIN")));
        assertEquals(1, entriesCaptor.getValue().size());
        assertEquals("SKILL.md", entriesCaptor.getValue().getFirst().path());
        assertEquals(10L, result.publishResult().skillId());
        verify(skillScoreSnapshotService).refreshSkillSnapshot(10L);
    }

    private void setField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }
}
