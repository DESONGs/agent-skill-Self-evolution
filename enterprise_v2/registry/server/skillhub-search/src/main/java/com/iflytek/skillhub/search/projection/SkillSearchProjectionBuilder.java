package com.iflytek.skillhub.search.projection;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshot;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotRepository;
import com.iflytek.skillhub.domain.label.LabelDefinition;
import com.iflytek.skillhub.domain.label.LabelDefinitionRepository;
import com.iflytek.skillhub.domain.label.LabelTranslation;
import com.iflytek.skillhub.domain.label.LabelTranslationRepository;
import com.iflytek.skillhub.domain.label.SkillLabel;
import com.iflytek.skillhub.domain.label.SkillLabelRepository;
import com.iflytek.skillhub.domain.namespace.Namespace;
import com.iflytek.skillhub.domain.namespace.NamespaceRepository;
import com.iflytek.skillhub.domain.security.SecurityAudit;
import com.iflytek.skillhub.domain.security.SecurityAuditRepository;
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
import com.iflytek.skillhub.domain.skill.service.SkillLifecycleProjectionService;
import com.iflytek.skillhub.search.SearchTextTokenizer;
import com.iflytek.skillhub.search.SkillSearchDocument;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class SkillSearchProjectionBuilder {
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
    private static final Set<String> RESERVED_FRONTMATTER_FIELDS = Set.of("name", "description", "version");
    private static final Set<String> KEYWORD_FIELD_NAMES = Set.of("keywords", "keyword", "tags", "tag");
    private static final BigDecimal NEUTRAL_SCORE = new BigDecimal("0.5000");

    private final NamespaceRepository namespaceRepository;
    private final SkillVersionRepository skillVersionRepository;
    private final SkillLifecycleProjectionService skillLifecycleProjectionService;
    private final SkillActionRepository skillActionRepository;
    private final SkillEnvironmentProfileRepository skillEnvironmentProfileRepository;
    private final SkillEvalSuiteRepository skillEvalSuiteRepository;
    private final SkillLabelRepository skillLabelRepository;
    private final LabelDefinitionRepository labelDefinitionRepository;
    private final LabelTranslationRepository labelTranslationRepository;
    private final SecurityAuditRepository securityAuditRepository;
    private final SkillScoreSnapshotRepository skillScoreSnapshotRepository;
    private final SearchTextTokenizer searchTextTokenizer;
    private final ObjectMapper objectMapper;

    public SkillSearchProjectionBuilder(
            NamespaceRepository namespaceRepository,
            SkillVersionRepository skillVersionRepository,
            SkillLifecycleProjectionService skillLifecycleProjectionService,
            SkillActionRepository skillActionRepository,
            SkillEnvironmentProfileRepository skillEnvironmentProfileRepository,
            SkillEvalSuiteRepository skillEvalSuiteRepository,
            SkillLabelRepository skillLabelRepository,
            LabelDefinitionRepository labelDefinitionRepository,
            LabelTranslationRepository labelTranslationRepository,
            SecurityAuditRepository securityAuditRepository,
            SkillScoreSnapshotRepository skillScoreSnapshotRepository,
            SearchTextTokenizer searchTextTokenizer) {
        this.namespaceRepository = namespaceRepository;
        this.skillVersionRepository = skillVersionRepository;
        this.skillLifecycleProjectionService = skillLifecycleProjectionService;
        this.skillActionRepository = skillActionRepository;
        this.skillEnvironmentProfileRepository = skillEnvironmentProfileRepository;
        this.skillEvalSuiteRepository = skillEvalSuiteRepository;
        this.skillLabelRepository = skillLabelRepository;
        this.labelDefinitionRepository = labelDefinitionRepository;
        this.labelTranslationRepository = labelTranslationRepository;
        this.securityAuditRepository = securityAuditRepository;
        this.skillScoreSnapshotRepository = skillScoreSnapshotRepository;
        this.searchTextTokenizer = searchTextTokenizer;
        this.objectMapper = new ObjectMapper();
    }

    public Optional<SkillSearchDocument> build(Skill skill) {
        if (skill == null) {
            return Optional.empty();
        }
        SkillLifecycleProjectionService.Projection projection =
                skillLifecycleProjectionService.projectPublishedSummaries(List.of(skill)).get(skill.getId());
        return build(skill, projection);
    }

    public Optional<SkillSearchDocument> build(
            Skill skill,
            SkillLifecycleProjectionService.Projection projection) {
        if (skill == null || projection == null || projection.publishedVersion() == null) {
            return Optional.empty();
        }

        Optional<SkillVersion> publishedVersion = resolvePublishedVersion(skill, projection);
        if (publishedVersion.isEmpty()) {
            return Optional.empty();
        }

        Optional<Namespace> namespaceOpt = Optional.ofNullable(namespaceRepository.findById(skill.getNamespaceId()))
                .orElse(Optional.empty());
        if (namespaceOpt.isEmpty()) {
            return Optional.empty();
        }

        SkillVersion version = publishedVersion.get();
        List<SkillLabel> skillLabels = Optional.ofNullable(skillLabelRepository.findBySkillId(skill.getId())).orElse(List.of());
        List<Long> labelIds = skillLabels.stream()
                .map(SkillLabel::getLabelId)
                .distinct()
                .toList();
        Map<Long, LabelDefinition> definitionsById = labelIds.isEmpty()
                ? Map.of()
                : Optional.ofNullable(labelDefinitionRepository.findByIdIn(labelIds)).orElse(List.of()).stream()
                        .collect(Collectors.toMap(LabelDefinition::getId, definition -> definition));
        Map<Long, List<LabelTranslation>> translationsByLabelId = labelIds.isEmpty()
                ? Map.of()
                : Optional.ofNullable(labelTranslationRepository.findByLabelIdIn(labelIds)).orElse(List.of()).stream()
                        .collect(Collectors.groupingBy(LabelTranslation::getLabelId, LinkedHashMap::new, Collectors.toList()));

        Set<String> labelSlugs = labelIds.stream()
                .map(definitionsById::get)
                .filter(Objects::nonNull)
                .map(LabelDefinition::getSlug)
                .filter(Objects::nonNull)
                .map(value -> value.trim().toLowerCase(Locale.ROOT))
                .filter(value -> !value.isBlank())
                .collect(Collectors.toCollection(TreeSet::new));

        Set<String> keywords = new TreeSet<>();
        List<String> searchParts = new ArrayList<>();
        addPart(searchParts, skill.getSlug());
        addPart(searchParts, skill.getSummary());
        extractParsedMetadata(version)
                .map(metadata -> metadata.get("frontmatter"))
                .map(this::asMap)
                .ifPresent(frontmatter -> appendFrontmatter(frontmatter, keywords, searchParts));
        appendLabelKeywords(labelIds, translationsByLabelId, keywords, searchParts);

        List<SkillAction> actions = Optional.ofNullable(skillActionRepository.findBySkillVersionId(version.getId())).orElse(List.of());
        List<SkillEnvironmentProfile> profiles = Optional.ofNullable(skillEnvironmentProfileRepository.findBySkillVersionId(version.getId())).orElse(List.of());
        List<SkillEvalSuite> evalSuites = Optional.ofNullable(skillEvalSuiteRepository.findBySkillVersionId(version.getId())).orElse(List.of());
        List<String> actionKinds = actions.stream()
                .map(SkillAction::getActionKind)
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .distinct()
                .sorted(String::compareToIgnoreCase)
                .toList();
        List<String> runtimeTags = buildRuntimeTags(profiles);
        List<String> toolTags = buildToolTags(profiles);

        actionKinds.forEach(value -> addPart(searchParts, value));
        runtimeTags.forEach(value -> addPart(searchParts, value));
        toolTags.forEach(value -> addPart(searchParts, value));
        evalSuites.stream()
                .map(SkillEvalSuite::getSuiteKey)
                .filter(Objects::nonNull)
                .forEach(value -> addPart(searchParts, value));

        SkillScoreSnapshot snapshot = Optional.ofNullable(skillScoreSnapshotRepository.findBySkillId(skill.getId()))
                .orElse(Optional.empty())
                .orElse(null);
        List<SecurityAudit> audits = Optional.ofNullable(securityAuditRepository.findLatestActiveByVersionId(version.getId()))
                .orElse(List.of());
        String scanVerdict = resolveScanVerdict(audits);
        String reviewState = version.getStatus() != null ? version.getStatus().name() : "UNKNOWN";
        Instant publishedAt = version.getPublishedAt();

        return Optional.of(new SkillSearchDocument(
                skill.getId(),
                skill.getNamespaceId(),
                namespaceOpt.get().getSlug(),
                skill.getOwnerId(),
                skill.getDisplayName() != null ? skill.getDisplayName() : skill.getSlug(),
                skill.getSummary(),
                searchTextTokenizer.enrichForIndex(String.join(" ", keywords)),
                searchTextTokenizer.enrichForIndex(String.join(" ", searchParts).trim()),
                null,
                skill.getVisibility().name(),
                skill.getStatus().name(),
                version.getId(),
                version.getVersion(),
                publishedAt,
                toJsonArray(new ArrayList<>(labelSlugs)),
                toJsonArray(runtimeTags),
                toJsonArray(toolTags),
                toJsonArray(actionKinds),
                scoreOrNeutral(snapshot == null ? null : snapshot.getTrustScore()),
                scoreOrNeutral(snapshot == null ? null : snapshot.getQualityScore()),
                scoreOrNeutral(snapshot == null ? null : snapshot.getFeedbackScore()),
                scoreOrNeutral(snapshot == null ? null : snapshot.getSuccessRate30d()),
                scanVerdict,
                reviewState
        ));
    }

    private Optional<SkillVersion> resolvePublishedVersion(Skill skill, SkillLifecycleProjectionService.Projection projection) {
        if (projection == null || projection.publishedVersion() == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(skillVersionRepository.findById(projection.publishedVersion().id()))
                .orElse(Optional.empty())
                .filter(version -> version.getSkillId().equals(skill.getId()))
                .filter(version -> version.getStatus() == SkillVersionStatus.PUBLISHED);
    }

    private Optional<Map<String, Object>> extractParsedMetadata(SkillVersion version) {
        String metadataJson = version.getParsedMetadataJson();
        if (metadataJson == null || metadataJson.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(objectMapper.readValue(metadataJson, MAP_TYPE));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> normalized = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() != null) {
                    normalized.put(String.valueOf(entry.getKey()), entry.getValue());
                }
            }
            return normalized;
        }
        return Map.of();
    }

    private void appendFrontmatter(Map<String, Object> frontmatter, Set<String> keywords, List<String> searchParts) {
        for (Map.Entry<String, Object> entry : frontmatter.entrySet()) {
            String fieldName = entry.getKey();
            Object value = entry.getValue();
            if (value == null) {
                continue;
            }
            String normalizedFieldName = fieldName.toLowerCase(Locale.ROOT);

            if (KEYWORD_FIELD_NAMES.contains(normalizedFieldName)) {
                flattenToStrings(value).forEach(keyword -> {
                    String normalized = keyword.trim();
                    if (!normalized.isBlank()) {
                        keywords.add(normalized);
                    }
                });
            }

            if (!RESERVED_FRONTMATTER_FIELDS.contains(normalizedFieldName)
                    && !KEYWORD_FIELD_NAMES.contains(normalizedFieldName)) {
                addPart(searchParts, fieldName);
                flattenToStrings(value).forEach(text -> addPart(searchParts, text));
            }
        }
    }

    private void appendLabelKeywords(
            List<Long> labelIds,
            Map<Long, List<LabelTranslation>> translationsByLabelId,
            Set<String> keywords,
            List<String> searchParts) {
        if (labelIds.isEmpty()) {
            return;
        }
        for (Long labelId : labelIds) {
            List<LabelTranslation> translations = translationsByLabelId.getOrDefault(labelId, List.of());
            for (LabelTranslation translation : translations) {
                addKeyword(keywords, translation.getDisplayName());
                addPart(searchParts, translation.getDisplayName());
            }
        }
    }

    private List<String> buildRuntimeTags(List<SkillEnvironmentProfile> profiles) {
        Set<String> tags = new LinkedHashSet<>();
        for (SkillEnvironmentProfile profile : profiles) {
            addTag(tags, profile.getProfileKey());
            addTag(tags, profile.getDisplayName());
            addTag(tags, profile.getRuntimeFamily());
            addTag(tags, profile.getRuntimeVersionRange());
            flattenJson(profile.getCapabilityTagsJson()).forEach(value -> addTag(tags, value));
            flattenJson(profile.getEnvSchemaJson()).forEach(value -> addTag(tags, value));
        }
        return new ArrayList<>(tags);
    }

    private List<String> buildToolTags(List<SkillEnvironmentProfile> profiles) {
        Set<String> tags = new LinkedHashSet<>();
        for (SkillEnvironmentProfile profile : profiles) {
            flattenJson(profile.getToolRequirementsJson()).forEach(value -> addTag(tags, value));
        }
        return new ArrayList<>(tags);
    }

    private String resolveScanVerdict(List<SecurityAudit> audits) {
        if (audits == null || audits.isEmpty()) {
            return "UNKNOWN";
        }
        if (audits.stream().anyMatch(audit -> audit.getVerdict() == com.iflytek.skillhub.domain.security.SecurityVerdict.BLOCKED)) {
            return "BLOCKED";
        }
        if (audits.stream().anyMatch(audit -> audit.getVerdict() == com.iflytek.skillhub.domain.security.SecurityVerdict.DANGEROUS)) {
            return "DANGEROUS";
        }
        if (audits.stream().anyMatch(audit -> audit.getVerdict() != null && "SUSPICIOUS".equalsIgnoreCase(audit.getVerdict().name()))) {
            return "SUSPICIOUS";
        }
        if (audits.stream().anyMatch(audit -> audit.getVerdict() != null && "SAFE".equalsIgnoreCase(audit.getVerdict().name()))) {
            return "SAFE";
        }
        return audits.getFirst().getVerdict() != null ? audits.getFirst().getVerdict().name() : "UNKNOWN";
    }

    private BigDecimal scoreOrNeutral(BigDecimal score) {
        return score == null ? NEUTRAL_SCORE : score;
    }

    private String toJsonArray(List<String> values) {
        try {
            return objectMapper.writeValueAsString(values == null ? List.of() : values);
        } catch (Exception e) {
            return "[]";
        }
    }

    private List<String> flattenJson(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            Object parsed = objectMapper.readValue(json, Object.class);
            return flattenToStrings(parsed).stream()
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .toList();
        } catch (Exception e) {
            return List.of();
        }
    }

    @SuppressWarnings("unchecked")
    private List<String> flattenToStrings(Object value) {
        if (value == null) {
            return List.of();
        }
        if (value instanceof String text) {
            return List.of(text);
        }
        if (value instanceof Number || value instanceof Boolean) {
            return List.of(String.valueOf(value));
        }
        if (value instanceof Map<?, ?> map) {
            List<String> values = new ArrayList<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() != null) {
                    values.add(String.valueOf(entry.getKey()));
                }
                if (entry.getValue() != null) {
                    values.addAll(flattenToStrings(entry.getValue()));
                }
            }
            return values;
        }
        if (value instanceof Collection<?> collection) {
            return collection.stream()
                    .filter(Objects::nonNull)
                    .flatMap(item -> flattenToStrings(item).stream())
                    .toList();
        }
        return List.of(String.valueOf(value));
    }

    private void addPart(List<String> parts, String value) {
        if (value == null) {
            return;
        }
        String normalized = value.trim();
        if (!normalized.isBlank()) {
            parts.add(normalized);
        }
    }

    private void addKeyword(Set<String> keywords, String value) {
        if (value == null) {
            return;
        }
        String normalized = value.trim();
        if (!normalized.isBlank()) {
            keywords.add(normalized);
        }
    }

    private void addTag(Set<String> tags, String value) {
        if (value == null) {
            return;
        }
        String normalized = value.trim();
        if (!normalized.isBlank()) {
            tags.add(normalized);
        }
    }
}
