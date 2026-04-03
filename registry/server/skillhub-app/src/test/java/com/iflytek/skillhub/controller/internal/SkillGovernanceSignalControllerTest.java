package com.iflytek.skillhub.controller.internal;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.domain.namespace.NamespaceMemberRepository;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalItemResponse;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalSummaryResponse;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalsResponse;
import com.iflytek.skillhub.service.SkillGovernanceSignalAppService;
import java.math.BigDecimal;
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
class SkillGovernanceSignalControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NamespaceMemberRepository namespaceMemberRepository;

    @MockBean
    private SkillGovernanceSignalAppService skillGovernanceSignalAppService;

    @Test
    void listSkillSignals_allowsApiTokenWithGovernanceScope() throws Exception {
        when(skillGovernanceSignalAppService.listSkillSignals(10))
                .thenReturn(new SkillGovernanceSignalsResponse(
                        new SkillGovernanceSignalSummaryResponse(1, 0, 0, 0, 0),
                        List.of(new SkillGovernanceSignalItemResponse(
                                1L,
                                "demo",
                                "Demo",
                                null,
                                null,
                                new BigDecimal("0.4000"),
                                new BigDecimal("0.5000"),
                                new BigDecimal("0.3000"),
                                new BigDecimal("0.5000"),
                                20L,
                                null,
                                List.of("LOW_SUCCESS", "QUEUE_REVIEW"),
                                List.of()
                        ))
                ));

        mockMvc.perform(get("/api/v1/internal/governance-signals/skills")
                        .param("limit", "10")
                        .with(authentication(authWithScope("skill:governance"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.summary.lowSuccessRateCount").value(1))
                .andExpect(jsonPath("$.data.items[0].signals[0]").value("LOW_SUCCESS"));
    }

    @Test
    void listSkillSignals_rejectsApiTokenWithoutGovernanceScope() throws Exception {
        mockMvc.perform(get("/api/v1/internal/governance-signals/skills")
                        .with(authentication(authWithScope("skill:read"))))
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
