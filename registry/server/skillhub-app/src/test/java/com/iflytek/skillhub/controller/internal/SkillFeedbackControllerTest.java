package com.iflytek.skillhub.controller.internal;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.domain.namespace.NamespaceMemberRepository;
import com.iflytek.skillhub.dto.internal.SkillFeedbackIngestionResponse;
import com.iflytek.skillhub.service.SkillFeedbackIngestionAppService;
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
class SkillFeedbackControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NamespaceMemberRepository namespaceMemberRepository;

    @MockBean
    private SkillFeedbackIngestionAppService skillFeedbackIngestionAppService;

    @Test
    void ingest_allowsApiTokenWithFeedbackScope() throws Exception {
        when(skillFeedbackIngestionAppService.ingest(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new SkillFeedbackIngestionResponse(
                        1L,
                        "fb-1",
                        7L,
                        10L,
                        "DOWNLOAD",
                        true,
                        Instant.parse("2026-04-03T00:00:00Z"),
                        Instant.parse("2026-04-03T00:00:00Z")
                ));

        mockMvc.perform(post("/api/v1/internal/skill-feedback")
                        .with(authentication(authWithScope("skill:feedback")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "dedupeKey":"fb-1",
                                  "feedbackSource":"DOWNLOAD",
                                  "subjectType":"SKILL_VERSION",
                                  "skillVersionId":10,
                                  "feedbackType":"DOWNLOAD",
                                  "success":true
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.dedupeKey").value("fb-1"))
                .andExpect(jsonPath("$.data.created").value(true));
    }

    @Test
    void ingest_rejectsApiTokenWithoutFeedbackScope() throws Exception {
        mockMvc.perform(post("/api/v1/internal/skill-feedback")
                        .with(authentication(authWithScope("skill:read")))
                        .contentType("application/json")
                        .content("""
                                {
                                  "dedupeKey":"fb-1",
                                  "feedbackSource":"DOWNLOAD",
                                  "subjectType":"SKILL_VERSION",
                                  "skillVersionId":10,
                                  "feedbackType":"DOWNLOAD"
                                }
                                """))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
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
