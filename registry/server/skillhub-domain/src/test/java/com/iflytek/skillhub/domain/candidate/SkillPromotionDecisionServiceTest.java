package com.iflytek.skillhub.domain.candidate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class SkillPromotionDecisionServiceTest {

    @Mock
    private SkillCandidateService skillCandidateService;
    @Mock
    private SkillPromotionDecisionRepository skillPromotionDecisionRepository;

    private SkillPromotionDecisionService service;

    @BeforeEach
    void setUp() {
        service = new SkillPromotionDecisionService(
                skillCandidateService,
                skillPromotionDecisionRepository,
                Clock.fixed(Instant.parse("2026-04-03T00:00:00Z"), ZoneOffset.UTC)
        );
    }

    @Test
    void appendDecision_shouldPersistAndMoveCandidateToPromotionPending() {
        SkillCandidate candidate = new SkillCandidate(
                "cand-1", "candidate-one", "WORKFLOW", "{}", "[]", null, null, null, null,
                "[]", null, "{}", "{}", null, null, null, null, "EVALUATED", null, null, null, null, "svc-1"
        );
        when(skillCandidateService.getCandidate(1L)).thenReturn(candidate);
        when(skillPromotionDecisionRepository.save(any(SkillPromotionDecision.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        SkillPromotionDecision decision = service.appendDecision(
                1L,
                new SkillPromotionDecisionService.DecisionCommand(
                        "PROMOTE",
                        "HUMAN_REVIEW",
                        "[\"good\"]",
                        "{\"overall\":0.9}",
                        "evidence/key.json",
                        "reviewer-1",
                        Instant.parse("2026-04-03T01:00:00Z")
                )
        );

        assertEquals("PROMOTE", decision.getDecision());
        assertEquals("HUMAN_REVIEW", decision.getDecisionMode());
        verify(skillCandidateService).transitionState(1L, SkillCandidateService.STATE_PROMOTION_PENDING);
    }
}
