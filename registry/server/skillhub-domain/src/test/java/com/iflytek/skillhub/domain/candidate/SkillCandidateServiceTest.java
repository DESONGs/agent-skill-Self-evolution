package com.iflytek.skillhub.domain.candidate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.lang.reflect.Field;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class SkillCandidateServiceTest {

    @Mock
    private SkillCandidateRepository skillCandidateRepository;

    private SkillCandidateService service;

    @BeforeEach
    void setUp() {
        service = new SkillCandidateService(skillCandidateRepository);
    }

    @Test
    void createCandidate_shouldPersistNormalizedDefaults() {
        when(skillCandidateRepository.findByCandidateKey("cand-1")).thenReturn(Optional.empty());
        when(skillCandidateRepository.save(any(SkillCandidate.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillCandidate created = service.createCandidate(new SkillCandidateService.UpsertCommand(
                "cand-1",
                "candidate-one",
                "WORKFLOW",
                null,
                null,
                "problem",
                "ops",
                "boundary",
                "trigger",
                null,
                "default",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                "svc-1"
        ));

        assertEquals("{}", created.getCandidateSpecJson());
        assertEquals("[]", created.getSourceRefsJson());
        assertEquals("CREATED", created.getPromotionState());
        assertEquals("svc-1", created.getCreatedBy());
    }

    @Test
    void updateCandidate_shouldMutateMutableFields() throws Exception {
        SkillCandidate candidate = new SkillCandidate(
                "cand-1", "candidate-one", "WORKFLOW", "{}", "[]", null, null, null, null,
                "[]", null, "{}", "{}", null, null, null, null, "CREATED", null, null, null, null, "svc-1"
        );
        setField(candidate, "id", 1L);

        when(skillCandidateRepository.findById(1L)).thenReturn(Optional.of(candidate));
        when(skillCandidateRepository.save(any(SkillCandidate.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SkillCandidate updated = service.updateCandidate(1L, new SkillCandidateService.UpsertCommand(
                null,
                "candidate-two",
                "MANUAL",
                "{\"entries\":[]}",
                null,
                "new problem",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                "LAB_READY",
                null,
                null,
                null
        ));

        assertEquals("candidate-two", updated.getCandidateSlug());
        assertEquals("MANUAL", updated.getSourceKind());
        assertEquals("{\"entries\":[]}", updated.getCandidateSpecJson());
        assertEquals("LAB_READY", updated.getPromotionState());
    }

    private void setField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }
}
