package com.iflytek.skillhub.search.projection;

import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshot;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotRepository;
import com.iflytek.skillhub.domain.label.LabelDefinition;
import com.iflytek.skillhub.domain.label.LabelDefinitionRepository;
import com.iflytek.skillhub.domain.label.LabelTranslation;
import com.iflytek.skillhub.domain.label.LabelTranslationRepository;
import com.iflytek.skillhub.domain.label.LabelType;
import com.iflytek.skillhub.domain.label.SkillLabel;
import com.iflytek.skillhub.domain.label.SkillLabelRepository;
import com.iflytek.skillhub.domain.namespace.Namespace;
import com.iflytek.skillhub.domain.namespace.NamespaceRepository;
import com.iflytek.skillhub.domain.security.ScannerType;
import com.iflytek.skillhub.domain.security.SecurityAudit;
import com.iflytek.skillhub.domain.security.SecurityAuditRepository;
import com.iflytek.skillhub.domain.security.SecurityVerdict;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillAction;
import com.iflytek.skillhub.domain.skill.SkillActionRepository;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfile;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfileRepository;
import com.iflytek.skillhub.domain.skill.SkillEvalSuite;
import com.iflytek.skillhub.domain.skill.SkillEvalSuiteRepository;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVersionRepository;
import com.iflytek.skillhub.domain.skill.SkillVersionStatus;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.service.SkillLifecycleProjectionService;
import com.iflytek.skillhub.search.SearchTextTokenizer;
import com.iflytek.skillhub.search.SkillSearchDocument;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SkillSearchProjectionBuilderTest {

    @Mock
    private NamespaceRepository namespaceRepository;

    @Mock
    private SkillVersionRepository skillVersionRepository;

    @Mock
    private SkillActionRepository skillActionRepository;

    @Mock
    private SkillEnvironmentProfileRepository skillEnvironmentProfileRepository;

    @Mock
    private SkillEvalSuiteRepository skillEvalSuiteRepository;

    @Mock
    private SkillLabelRepository skillLabelRepository;

    @Mock
    private LabelDefinitionRepository labelDefinitionRepository;

    @Mock
    private LabelTranslationRepository labelTranslationRepository;

    @Mock
    private SecurityAuditRepository securityAuditRepository;

    @Mock
    private SkillScoreSnapshotRepository skillScoreSnapshotRepository;

    private SkillSearchProjectionBuilder builder;

    @BeforeEach
    void setUp() {
        builder = new SkillSearchProjectionBuilder(
                namespaceRepository,
                skillVersionRepository,
                new SkillLifecycleProjectionService(skillVersionRepository),
                skillActionRepository,
                skillEnvironmentProfileRepository,
                skillEvalSuiteRepository,
                skillLabelRepository,
                labelDefinitionRepository,
                labelTranslationRepository,
                securityAuditRepository,
                skillScoreSnapshotRepository,
                new SearchTextTokenizer()
        );
    }

    @Test
    void buildShouldIncludeRegistryAssetSignalsAndRankingFields() {
        Skill skill = new Skill(1L, "smart-agent", "owner-1", SkillVisibility.PUBLIC);
        setField(skill, "id", 10L);
        skill.setDisplayName("Smart Agent");
        skill.setSummary("Builds workflows");
        skill.setLatestVersionId(100L);

        Namespace namespace = new Namespace("team-a", "Team A", "owner-1");
        setField(namespace, "id", 1L);
        when(namespaceRepository.findById(1L)).thenReturn(Optional.of(namespace));

        SkillVersion version = new SkillVersion(10L, "1.2.3", "owner-1");
        version.setStatus(SkillVersionStatus.PUBLISHED);
        setField(version, "id", 100L);
        version.setPublishedAt(Instant.parse("2026-04-03T10:15:30Z"));
        version.setParsedMetadataJson("""
                {
                  "frontmatter": {
                    "keywords": ["assistant", "automation"],
                    "tags": ["workflow"],
                    "owner": "ignored"
                  }
                }
                """);

        when(skillVersionRepository.findByIdIn(List.of(100L))).thenReturn(List.of(version));
        when(skillVersionRepository.findById(100L)).thenReturn(Optional.of(version));
        when(skillLabelRepository.findBySkillId(10L)).thenReturn(List.of(new SkillLabel(10L, 7L, "owner-1")));
        LabelDefinition labelDefinition = new LabelDefinition("code-generation", LabelType.RECOMMENDED, true, 1, "owner-1");
        setField(labelDefinition, "id", 7L);
        when(labelDefinitionRepository.findByIdIn(List.of(7L))).thenReturn(List.of(labelDefinition));
        when(labelTranslationRepository.findByLabelIdIn(List.of(7L))).thenReturn(List.of(new LabelTranslation(7L, "en-US", "Code Generation")));

        SkillAction action = new SkillAction(100L, "main", "TOOL", "/entry", "owner-1");
        action.setDisplayName("Main");
        when(skillActionRepository.findBySkillVersionId(100L)).thenReturn(List.of(action));

        SkillEnvironmentProfile profile = new SkillEnvironmentProfile(100L, "default", "owner-1");
        profile.setDisplayName("Default");
        profile.setRuntimeFamily("python");
        profile.setRuntimeVersionRange("3.11");
        profile.setToolRequirementsJson("[\"node\",\"uv\"]");
        profile.setCapabilityTagsJson("[\"resilient\"]");
        when(skillEnvironmentProfileRepository.findBySkillVersionId(100L)).thenReturn(List.of(profile));

        SkillEvalSuite suite = new SkillEvalSuite(100L, "smoke", "EVAL", "HIGH", "owner-1");
        suite.setDisplayName("Smoke");
        when(skillEvalSuiteRepository.findBySkillVersionId(100L)).thenReturn(List.of(suite));

        SkillScoreSnapshot snapshot = new SkillScoreSnapshot(10L);
        snapshot.setTrustScore(new BigDecimal("0.9100"));
        snapshot.setQualityScore(new BigDecimal("0.8200"));
        snapshot.setFeedbackScore(new BigDecimal("0.7300"));
        snapshot.setSuccessRate30d(new BigDecimal("0.8800"));
        when(skillScoreSnapshotRepository.findBySkillId(10L)).thenReturn(Optional.of(snapshot));

        SecurityAudit audit = new SecurityAudit(100L, ScannerType.SKILL_SCANNER);
        audit.setVerdict(SecurityVerdict.SAFE);
        audit.setIsSafe(true);
        when(securityAuditRepository.findLatestActiveByVersionId(100L)).thenReturn(List.of(audit));

        SkillSearchDocument document = builder.build(skill).orElseThrow();

        assertThat(document.skillId()).isEqualTo(10L);
        assertThat(document.namespaceSlug()).isEqualTo("team-a");
        assertThat(document.latestPublishedVersionId()).isEqualTo(100L);
        assertThat(document.latestPublishedVersion()).isEqualTo("1.2.3");
        assertThat(document.publishedAt()).isEqualTo(Instant.parse("2026-04-03T10:15:30Z"));
        assertThat(document.labelSlugs()).contains("code-generation");
        assertThat(document.runtimeTags()).contains("python");
        assertThat(document.toolTags()).contains("node");
        assertThat(document.actionKinds()).contains("TOOL");
        assertThat(document.trustScore()).isEqualByComparingTo("0.9100");
        assertThat(document.qualityScore()).isEqualByComparingTo("0.8200");
        assertThat(document.feedbackScore()).isEqualByComparingTo("0.7300");
        assertThat(document.successRate30d()).isEqualByComparingTo("0.8800");
        assertThat(document.scanVerdict()).isEqualTo("SAFE");
        assertThat(document.reviewState()).isEqualTo("PUBLISHED");
        assertThat(document.searchText()).contains("smart-agent");
        assertThat(document.keywords()).contains("Code Generation");
    }

    private void setField(Object target, String fieldName, Object value) {
        try {
            java.lang.reflect.Field field = target.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(target, value);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
