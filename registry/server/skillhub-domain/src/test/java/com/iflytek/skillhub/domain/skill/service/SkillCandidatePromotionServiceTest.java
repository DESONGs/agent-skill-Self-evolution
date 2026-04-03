package com.iflytek.skillhub.domain.skill.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecision;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecisionRepository;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.storage.ObjectStorageService;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.jupiter.api.Test;

class SkillCandidatePromotionServiceTest {

    @Test
    void publish_shouldReusePublishChainAndUpdateCandidateLinkage() throws Exception {
        SkillCandidateRepository candidateRepository = mock(SkillCandidateRepository.class);
        SkillPromotionDecisionRepository decisionRepository = mock(SkillPromotionDecisionRepository.class);
        ObjectStorageService objectStorageService = mock(ObjectStorageService.class);
        SkillPublishService publishService = mock(SkillPublishService.class);
        SkillScoreSnapshotService skillScoreSnapshotService = mock(SkillScoreSnapshotService.class);

        SkillCandidate candidate = new SkillCandidate(
                "cand-1",
                "candidate-one",
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
                "candidates/cand-1/bundle.zip",
                null,
                null,
                null,
                "PROMOTION_PENDING",
                null,
                null,
                null,
                null,
                "creator-1"
        );
        setField(candidate, "id", 1L);

        SkillPromotionDecision decision = new SkillPromotionDecision(
                1L,
                "PROMOTE",
                "HUMAN_REVIEW",
                "[]",
                "{}",
                null,
                "reviewer-1",
                java.time.Instant.parse("2026-04-03T00:00:00Z")
        );

        SkillVersion publishedVersion = new SkillVersion(8L, "1.0.0", "publisher-1");
        setField(publishedVersion, "id", 10L);

        when(candidateRepository.findById(1L)).thenReturn(java.util.Optional.of(candidate));
        when(decisionRepository.findBySkillCandidateIdOrderByDecidedAtDesc(1L)).thenReturn(List.of(decision));
        when(objectStorageService.getObject("candidates/cand-1/bundle.zip"))
                .thenReturn(new ByteArrayInputStream(zip(
                        "candidate-one/SKILL.md", "# Demo\n",
                        "candidate-one/actions.yaml", "actions: []\n"
                )));
        when(publishService.publishFromEntries(eq("team-a"), any(), eq("publisher-1"), eq(SkillVisibility.PUBLIC), eq(Set.of("USER"))))
                .thenReturn(new SkillPublishService.PublishResult(8L, "candidate-one", publishedVersion));
        when(candidateRepository.save(any(SkillCandidate.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillCandidatePromotionService service = new SkillCandidatePromotionService(
                candidateRepository,
                decisionRepository,
                objectStorageService,
                publishService,
                skillScoreSnapshotService
        );

        SkillCandidatePromotionService.CandidatePublishResult result = service.publish(
                1L,
                "team-a",
                SkillVisibility.PUBLIC,
                "publisher-1",
                Set.of("USER")
        );

        assertThat(result.skillId()).isEqualTo(8L);
        assertThat(result.version().getId()).isEqualTo(10L);
        assertThat(result.candidate().getPublishedSkillId()).isEqualTo(8L);
        assertThat(result.candidate().getPublishedVersionId()).isEqualTo(10L);
        assertThat(result.candidate().getPromotionState()).isEqualTo("PUBLISHED");
        verify(skillScoreSnapshotService).refreshSkillSnapshot(8L);
    }

    private byte[] zip(String path1, String content1, String path2, String content2) throws Exception {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        try (ZipOutputStream zipOutputStream = new ZipOutputStream(outputStream, StandardCharsets.UTF_8)) {
            zipOutputStream.putNextEntry(new ZipEntry(path1));
            zipOutputStream.write(content1.getBytes(StandardCharsets.UTF_8));
            zipOutputStream.closeEntry();
            zipOutputStream.putNextEntry(new ZipEntry(path2));
            zipOutputStream.write(content2.getBytes(StandardCharsets.UTF_8));
            zipOutputStream.closeEntry();
        }
        return outputStream.toByteArray();
    }

    private void setField(Object target, String fieldName, Object value) {
        try {
            var field = target.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException ex) {
            throw new IllegalStateException(ex);
        }
    }
}
