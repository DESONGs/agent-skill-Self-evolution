package com.iflytek.skillhub.controller;

import com.iflytek.skillhub.domain.namespace.NamespaceMemberRepository;
import com.iflytek.skillhub.dto.SkillLifecycleVersionResponse;
import com.iflytek.skillhub.dto.SkillSummaryResponse;
import com.iflytek.skillhub.service.SkillSearchAppService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SkillSearchControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NamespaceMemberRepository namespaceMemberRepository;

    @MockBean
    private SkillSearchAppService skillSearchAppService;

    @Test
    void searchShouldUseUnifiedEnvelopeAndItemsField() throws Exception {
        when(skillSearchAppService.search(
                eq("review"),
                eq("global"),
                eq("newest"),
                eq(0),
                eq(20),
                eq(null),
                any(),
                any()))
                .thenReturn(new SkillSearchAppService.SearchResponse(List.of(), 0, 0, 20));

        mockMvc.perform(get("/api/web/skills")
                        .param("q", "review")
                        .param("namespace", "global"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.total").value(0))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.requestId").isNotEmpty());
    }

    @Test
    void searchShouldPassExplicitSortPageAndSize() throws Exception {
        when(skillSearchAppService.search(
                eq(null),
                eq(null),
                eq("newest"),
                eq(0),
                eq(12),
                eq(null),
                any(),
                any()))
                .thenReturn(new SkillSearchAppService.SearchResponse(List.of(), 0, 0, 12));

        mockMvc.perform(get("/api/web/skills")
                        .param("sort", "newest")
                        .param("page", "0")
                        .param("size", "12"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.size").value(12))
                .andExpect(jsonPath("$.data.page").value(0));
    }

    @Test
    void searchShouldPassLabelFilters() throws Exception {
        when(skillSearchAppService.search(
                eq("review"),
                eq(null),
                eq("newest"),
                eq(0),
                eq(20),
                eq(List.of("code-generation", "official")),
                any(),
                any()))
                .thenReturn(new SkillSearchAppService.SearchResponse(List.of(), 0, 0, 20));

        mockMvc.perform(get("/api/web/skills")
                        .param("q", "review")
                .param("label", "code-generation")
                .param("label", "official"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray());
    }

    @Test
    void searchShouldSerializeAdditiveResponseFields() throws Exception {
        when(skillSearchAppService.search(
                eq("review"),
                eq(null),
                eq("newest"),
                eq(0),
                eq(20),
                eq(null),
                any(),
                any()))
                .thenReturn(new SkillSearchAppService.SearchResponse(
                        List.of(new SkillSummaryResponse(
                                1L,
                                "skill-a",
                                "Skill A",
                                "Summary",
                                "ACTIVE",
                                12L,
                                3,
                                java.math.BigDecimal.valueOf(4.8),
                                9,
                                "team-a",
                                java.time.Instant.parse("2026-04-03T10:15:30Z"),
                                false,
                                new SkillLifecycleVersionResponse(7L, "1.0.0", "PUBLISHED"),
                                new SkillLifecycleVersionResponse(7L, "1.0.0", "PUBLISHED"),
                                null,
                                "PUBLISHED",
                                List.of("guide", "official"),
                                List.of("runtime:python"),
                                List.of("tooling"),
                                java.math.BigDecimal.valueOf(0.92),
                                java.math.BigDecimal.valueOf(0.81)
                        )),
                        1,
                        0,
                        20));

        mockMvc.perform(get("/api/web/skills")
                        .param("q", "review"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].labels[0]").value("guide"))
                .andExpect(jsonPath("$.data.items[0].runtimeTags[0]").value("runtime:python"))
                .andExpect(jsonPath("$.data.items[0].actionKinds[0]").value("tooling"))
                .andExpect(jsonPath("$.data.items[0].successRate").value(0.92))
                .andExpect(jsonPath("$.data.items[0].trustScore").value(0.81));
    }
}
