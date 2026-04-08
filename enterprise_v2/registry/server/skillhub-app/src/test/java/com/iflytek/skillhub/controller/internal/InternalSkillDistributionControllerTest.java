package com.iflytek.skillhub.controller.internal;

import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.domain.namespace.NamespaceMemberRepository;
import com.iflytek.skillhub.domain.namespace.NamespaceRole;
import com.iflytek.skillhub.dto.SkillDistributionResponse;
import com.iflytek.skillhub.dto.internal.InternalSkillDistributionResponse;
import com.iflytek.skillhub.service.SkillDistributionAppService;
import java.time.Instant;
import java.util.List;
import java.util.Map;
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

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalSkillDistributionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NamespaceMemberRepository namespaceMemberRepository;

    @MockBean
    private SkillDistributionAppService skillDistributionAppService;

    @Test
    void getLatestDistribution_allowsApiTokenWithInternalReadScope() throws Exception {
        when(skillDistributionAppService.getLatestInternalDistribution(
                eq("team"),
                eq("demo"),
                eq("svc-1"),
                eq(Map.<Long, NamespaceRole>of())))
                .thenReturn(new InternalSkillDistributionResponse(
                        1L,
                        "team",
                        "demo",
                        "Demo",
                        "Internal distribution",
                        "PUBLIC",
                        false,
                        new SkillDistributionResponse.VersionDescriptor(
                                10L,
                                "1.0.0",
                                "PUBLISHED",
                                "PUBLIC",
                                Instant.parse("2026-03-12T12:00:00Z"),
                                2,
                                128L,
                                true,
                                true,
                                "{\"name\":\"demo\"}",
                                "[{\"path\":\"SKILL.md\"}]"
                        ),
                        new InternalSkillDistributionResponse.InternalBundleDescriptor(
                                "/api/v1/skills/team/demo/download",
                                null,
                                "packages/1/10/bundle.zip",
                                "application/zip",
                                128L,
                                "demo-1.0.0.zip",
                                false,
                                "READY",
                                "sha256",
                                "manifest-sha",
                                Instant.parse("2026-03-12T12:00:00Z")
                        ),
                        List.of(),
                        List.of("latest"),
                        List.of(),
                        List.of(),
                        List.of(),
                        List.of(),
                        List.of()
                ));

        PlatformPrincipal principal = new PlatformPrincipal(
                "svc-1",
                "Service",
                "svc@example.com",
                "",
                "api_token",
                Set.of("USER")
        );
        var auth = new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of(
                        new SimpleGrantedAuthority("ROLE_USER"),
                        new SimpleGrantedAuthority("SCOPE_skill:internal-read")
                )
        );

        mockMvc.perform(get("/api/v1/internal/skills/team/demo/distribution").with(authentication(auth)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.bundle.storageKey").value("packages/1/10/bundle.zip"))
                .andExpect(jsonPath("$.data.version.version").value("1.0.0"));
    }

    @Test
    void getLatestDistribution_rejectsApiTokenWithoutInternalReadScope() throws Exception {
        PlatformPrincipal principal = new PlatformPrincipal(
                "svc-1",
                "Service",
                "svc@example.com",
                "",
                "api_token",
                Set.of("USER")
        );
        var auth = new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of(
                        new SimpleGrantedAuthority("ROLE_USER"),
                        new SimpleGrantedAuthority("SCOPE_skill:read")
                )
        );

        mockMvc.perform(get("/api/v1/internal/skills/team/demo/distribution").with(authentication(auth)))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }
}
