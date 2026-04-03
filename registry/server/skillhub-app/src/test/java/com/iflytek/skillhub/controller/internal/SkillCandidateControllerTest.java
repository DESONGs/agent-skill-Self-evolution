package com.iflytek.skillhub.controller.internal;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.domain.namespace.NamespaceMemberRepository;
import com.iflytek.skillhub.dto.internal.SkillCandidateDetailResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidatePublishResponse;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionResponse;
import com.iflytek.skillhub.service.SkillCandidateAppService;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SkillCandidateControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NamespaceMemberRepository namespaceMemberRepository;

    @MockBean
    private SkillCandidateAppService skillCandidateAppService;

    @Test
    void createCandidate_allowsApiTokenWithCandidateScope() throws Exception {
        when(skillCandidateAppService.create(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq("svc-1")))
                .thenReturn(new SkillCandidateDetailResponse(
                        1L,
                        "cand-1",
                        "candidate-one",
                        "{}",
                        "WORKFLOW",
                        "[]",
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
                        null,
                        "CREATED",
                        null,
                        null,
                        null,
                        null,
                        "svc-1",
                        Instant.parse("2026-04-03T00:00:00Z"),
                        Instant.parse("2026-04-03T00:00:00Z"),
                        List.of()
                ));

        mockMvc.perform(post("/api/v1/internal/candidates")
                        .with(authentication(authWithScope("skill:candidate")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "candidateKey":"cand-1",
                                  "candidateSlug":"candidate-one",
                                  "sourceKind":"WORKFLOW",
                                  "candidateSpecJson":"{}"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.candidateKey").value("cand-1"));
    }

    @Test
    void createCandidate_rejectsApiTokenWithoutCandidateScope() throws Exception {
        mockMvc.perform(post("/api/v1/internal/candidates")
                        .with(authentication(authWithScope("skill:read")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "candidateKey":"cand-1",
                                  "candidateSlug":"candidate-one",
                                  "sourceKind":"WORKFLOW"
                                }
                                """))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    void getCandidate_allowsApiTokenWithInternalReadScope() throws Exception {
        when(skillCandidateAppService.get(1L))
                .thenReturn(new SkillCandidateDetailResponse(
                        1L,
                        "cand-1",
                        "candidate-one",
                        "{}",
                        "WORKFLOW",
                        "[]",
                        "Problem",
                        "Makers",
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
                        "PROMOTION_PENDING",
                        null,
                        null,
                        null,
                        null,
                        "svc-1",
                        Instant.parse("2026-04-03T00:00:00Z"),
                        Instant.parse("2026-04-03T00:00:00Z"),
                        List.of()
                ));

        mockMvc.perform(get("/api/v1/internal/candidates/1")
                        .with(authentication(authWithScope("skill:internal-read"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.candidateKey").value("cand-1"))
                .andExpect(jsonPath("$.data.promotionState").value("PROMOTION_PENDING"));
    }

    @Test
    void appendDecision_allowsApiTokenWithCandidateScope() throws Exception {
        when(skillCandidateAppService.createDecision(org.mockito.ArgumentMatchers.eq(1L), org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq("svc-1")))
                .thenReturn(new SkillPromotionDecisionResponse(
                        10L,
                        1L,
                        "PROMOTE",
                        "HUMAN_REVIEW",
                        "[]",
                        "{}",
                        null,
                        "svc-1",
                        Instant.parse("2026-04-03T00:00:00Z"),
                        Instant.parse("2026-04-03T00:00:00Z")
                ));

        mockMvc.perform(post("/api/v1/internal/candidates/1/promotion-decisions")
                        .with(authentication(authWithScope("skill:candidate")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "decision":"PROMOTE",
                                  "decisionMode":"HUMAN_REVIEW"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.decision").value("PROMOTE"));
    }

    @Test
    void publishCandidate_allowsApiTokenWithCandidateScope() throws Exception {
        when(skillCandidateAppService.publish(org.mockito.ArgumentMatchers.eq(1L), org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.any()))
                .thenReturn(new SkillCandidatePublishResponse(
                        1L,
                        "PUBLISHED",
                        88L,
                        101L,
                        "team-a",
                        "cand-1",
                        "1.0.0",
                        "PUBLISHED"
                ));

        mockMvc.perform(post("/api/v1/internal/candidates/1/publish")
                        .with(authentication(authWithScope("skill:candidate")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "namespace":"team-a",
                                  "visibility":"PUBLIC"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.promotionState").value("PUBLISHED"))
                .andExpect(jsonPath("$.data.publishedSkillId").value(88));
    }

    private UsernamePasswordAuthenticationToken authWithScope(String scope) {
        PlatformPrincipal principal = new PlatformPrincipal(
                "svc-1",
                "Service",
                "svc@example.com",
                "",
                "api_token",
                Set.of("USER")
        );
        return new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of(
                        new SimpleGrantedAuthority("ROLE_USER"),
                        new SimpleGrantedAuthority("SCOPE_" + scope)
                )
        );
    }
}
