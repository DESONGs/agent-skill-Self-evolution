package com.iflytek.skillhub.domain.skill.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.iflytek.skillhub.domain.skill.validation.PackageEntry;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.yaml.snakeyaml.Yaml;

/**
 * Parses optional package metadata files such as {@code actions.yaml} and
 * {@code evals/*} into normalized asset records that the registry can persist.
 *
 * <p>This service only normalizes asset metadata. It does not perform any
 * runtime orchestration or persistence.
 */
@Service
public class SkillAssetNormalizationService {

    public record AssetNormalizationResult(
            List<NormalizedEnvironmentProfile> environmentProfiles,
            List<NormalizedAction> actions,
            List<NormalizedEvalSuite> evalSuites
    ) {
    }

    public record NormalizedEnvironmentProfile(
            String profileKey,
            String displayName,
            String runtimeFamily,
            String runtimeVersionRange,
            String toolRequirementsJson,
            String capabilityTagsJson,
            String osConstraintsJson,
            String networkPolicy,
            String filesystemPolicy,
            String sandboxMode,
            String resourceLimitsJson,
            String envSchemaJson,
            boolean defaultProfile
    ) {
    }

    public record NormalizedAction(
            String actionId,
            String displayName,
            String actionKind,
            String entryPath,
            String runtimeFamily,
            String environmentProfileKey,
            Integer timeoutSec,
            String sandboxMode,
            boolean allowNetwork,
            String inputSchemaJson,
            String outputSchemaJson,
            String sideEffectsJson,
            String idempotencyMode,
            boolean defaultAction
    ) {
    }

    public record NormalizedEvalSuite(
            String suiteKey,
            String displayName,
            String suiteType,
            String entryPath,
            String gateLevel,
            String configJson,
            String successCriteriaJson
    ) {
    }

    private static final String ACTIONS_PATH = "actions.yaml";
    private static final String ACTIONS_ALT_PATH = "actions.yml";
    private static final String INTERFACE_PATH = "agents/interface.yaml";
    private static final String INTERFACE_ALT_PATH = "agents/interface.yml";

    private final ObjectMapper objectMapper;
    private final Yaml yaml;

    public SkillAssetNormalizationService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.yaml = new Yaml();
    }

    public AssetNormalizationResult normalize(List<PackageEntry> entries) {
        if (entries == null || entries.isEmpty()) {
            return new AssetNormalizationResult(List.of(), List.of(), List.of());
        }

        PackageEntry actionsEntry = findFirst(entries, ACTIONS_PATH, ACTIONS_ALT_PATH);
        PackageEntry interfaceEntry = findFirst(entries, INTERFACE_PATH, INTERFACE_ALT_PATH);

        Map<String, Object> actionsDoc = parseYaml(actionsEntry);
        Map<String, Object> interfaceDoc = parseYaml(interfaceEntry);

        List<NormalizedEnvironmentProfile> environmentProfiles =
                normalizeEnvironmentProfiles(actionsDoc, interfaceDoc);
        List<NormalizedAction> actions = normalizeActions(actionsDoc, environmentProfiles);
        List<NormalizedEvalSuite> evalSuites = normalizeEvalSuites(entries);

        return new AssetNormalizationResult(environmentProfiles, actions, evalSuites);
    }

    private PackageEntry findFirst(List<PackageEntry> entries, String... paths) {
        Set<String> acceptable = Set.of(paths);
        return entries.stream()
                .filter(entry -> acceptable.contains(entry.path()))
                .findFirst()
                .orElse(null);
    }

    private Map<String, Object> parseYaml(PackageEntry entry) {
        if (entry == null) {
            return Map.of();
        }
        Object loaded = yaml.load(new String(entry.content(), StandardCharsets.UTF_8));
        if (loaded instanceof Map<?, ?> rawMap) {
            return toStringObjectMap(rawMap);
        }
        return Map.of();
    }

    private List<NormalizedEnvironmentProfile> normalizeEnvironmentProfiles(
            Map<String, Object> actionsDoc,
            Map<String, Object> interfaceDoc) {
        List<Map<String, Object>> profileMaps = new ArrayList<>();
        profileMaps.addAll(asMapList(actionsDoc.get("environment_profiles")));
        profileMaps.addAll(asMapList(actionsDoc.get("environments")));
        profileMaps.addAll(asMapList(interfaceDoc.get("environment_profiles")));

        List<NormalizedEnvironmentProfile> profiles = new ArrayList<>();
        Set<String> seenKeys = new LinkedHashSet<>();
        for (Map<String, Object> profileMap : profileMaps) {
            String profileKey = normalizedText(profileMap.get("key"));
            if (profileKey == null) {
                profileKey = normalizedText(profileMap.get("id"));
            }
            if (profileKey == null) {
                profileKey = "default";
            }
            if (!seenKeys.add(profileKey)) {
                continue;
            }

            profiles.add(new NormalizedEnvironmentProfile(
                    profileKey,
                    firstNonBlank(
                            normalizedText(profileMap.get("display_name")),
                            normalizedText(profileMap.get("displayName")),
                            profileKey),
                    firstNonBlank(
                            normalizedText(profileMap.get("runtime_family")),
                            normalizedText(profileMap.get("runtimeFamily")),
                            normalizedText(interfaceDoc.get("runtime")),
                            "generic"),
                    firstNonBlank(
                            normalizedText(profileMap.get("runtime_version_range")),
                            normalizedText(profileMap.get("runtimeVersionRange")),
                            normalizedText(profileMap.get("runtime_version"))),
                    json(profileMap.get("tool_requirements")),
                    json(profileMap.get("capability_tags")),
                    json(profileMap.get("os_constraints")),
                    firstNonBlank(
                            normalizedText(profileMap.get("network_policy")),
                            boolValue(profileMap.get("allow_network")) ? "ENABLED" : "DISABLED"),
                    normalizedText(profileMap.get("filesystem_policy")),
                    firstNonBlank(
                            normalizedText(profileMap.get("sandbox")),
                            normalizedText(profileMap.get("sandbox_mode")),
                            "workspace-write"),
                    json(profileMap.get("resource_limits")),
                    json(profileMap.get("env_schema")),
                    boolValue(profileMap.get("default")) || profiles.isEmpty()
            ));
        }

        if (!profiles.isEmpty()) {
            return profiles;
        }

        String inferredRuntime = "generic";
        List<Map<String, Object>> actionMaps = asMapList(actionsDoc.get("actions"));
        if (!actionMaps.isEmpty()) {
            inferredRuntime = firstNonBlank(
                    normalizedText(actionMaps.get(0).get("runtime")),
                    normalizedText(interfaceDoc.get("runtime")),
                    "generic");
        } else if (normalizedText(interfaceDoc.get("runtime")) != null) {
            inferredRuntime = normalizedText(interfaceDoc.get("runtime"));
        }

        return List.of(new NormalizedEnvironmentProfile(
                "default",
                "default",
                inferredRuntime,
                null,
                null,
                null,
                null,
                "DISABLED",
                null,
                "workspace-write",
                null,
                null,
                true
        ));
    }

    private List<NormalizedAction> normalizeActions(
            Map<String, Object> actionsDoc,
            List<NormalizedEnvironmentProfile> environmentProfiles) {
        List<Map<String, Object>> actionMaps = asMapList(actionsDoc.get("actions"));
        if (actionMaps.isEmpty()) {
            return List.of();
        }

        String defaultProfileKey = environmentProfiles.stream()
                .filter(NormalizedEnvironmentProfile::defaultProfile)
                .map(NormalizedEnvironmentProfile::profileKey)
                .findFirst()
                .orElse("default");

        List<NormalizedAction> actions = new ArrayList<>();
        for (int i = 0; i < actionMaps.size(); i++) {
            Map<String, Object> actionMap = actionMaps.get(i);
            String actionId = firstNonBlank(
                    normalizedText(actionMap.get("id")),
                    "action-" + (i + 1));
            String profileKey = firstNonBlank(
                    normalizedText(actionMap.get("environment_profile")),
                    normalizedText(actionMap.get("environmentProfile")),
                    defaultProfileKey);
            actions.add(new NormalizedAction(
                    actionId,
                    firstNonBlank(
                            normalizedText(actionMap.get("display_name")),
                            normalizedText(actionMap.get("displayName")),
                            actionId),
                    firstNonBlank(normalizedUpperText(actionMap.get("kind")), "SCRIPT"),
                    firstNonBlank(
                            normalizedText(actionMap.get("entry")),
                            normalizedText(actionMap.get("path")),
                            normalizedText(actionMap.get("handler")),
                            actionId),
                    firstNonBlank(normalizedText(actionMap.get("runtime")), "generic"),
                    profileKey,
                    intValue(actionMap.get("timeout_sec")),
                    firstNonBlank(
                            normalizedText(actionMap.get("sandbox")),
                            normalizedText(actionMap.get("sandbox_mode")),
                            "workspace-write"),
                    boolValue(actionMap.get("allow_network")),
                    json(actionMap.get("input_schema")),
                    json(actionMap.get("output_schema")),
                    json(actionMap.get("side_effects")),
                    firstNonBlank(normalizedText(actionMap.get("idempotency")), "best_effort"),
                    boolValue(actionMap.get("default")) || i == 0
            ));
        }
        return actions;
    }

    private List<NormalizedEvalSuite> normalizeEvalSuites(List<PackageEntry> entries) {
        return entries.stream()
                .filter(entry -> entry.path().startsWith("evals/"))
                .sorted(Comparator.comparing(PackageEntry::path))
                .map(entry -> {
                    String filename = entry.path().substring("evals/".length());
                    String suiteKey = suiteKey(filename);
                    return new NormalizedEvalSuite(
                            suiteKey,
                            suiteKey.replace('-', ' '),
                            inferSuiteType(filename),
                            entry.path(),
                            "OPTIONAL",
                            contentJson(entry),
                            null
                    );
                })
                .toList();
    }

    private String inferSuiteType(String filename) {
        String normalized = filename.toLowerCase(Locale.ROOT);
        if (normalized.contains("trigger")) {
            return "TRIGGER";
        }
        if (normalized.contains("boundary")) {
            return "BOUNDARY";
        }
        if (normalized.contains("resource")) {
            return "RESOURCE";
        }
        if (normalized.contains("governance")) {
            return "GOVERNANCE";
        }
        if (normalized.contains("security") || normalized.contains("safety")) {
            return "SECURITY";
        }
        if (normalized.contains("pack")) {
            return "PACKAGING";
        }
        if (normalized.contains("promotion")) {
            return "PROMOTION";
        }
        return "STRUCTURE";
    }

    private String suiteKey(String filename) {
        String normalized = filename.replace('\\', '/');
        int slash = normalized.lastIndexOf('/');
        if (slash >= 0) {
            normalized = normalized.substring(slash + 1);
        }
        int dot = normalized.lastIndexOf('.');
        if (dot > 0) {
            normalized = normalized.substring(0, dot);
        }
        return normalized.trim().toLowerCase(Locale.ROOT).replace('_', '-').replace(' ', '-');
    }

    private String contentJson(PackageEntry entry) {
        if (entry == null || entry.content() == null || entry.content().length == 0) {
            return null;
        }
        String lower = entry.path().toLowerCase(Locale.ROOT);
        String content = new String(entry.content(), StandardCharsets.UTF_8).trim();
        if (content.isBlank()) {
            return null;
        }
        if (lower.endsWith(".json")) {
            return content;
        }
        Map<String, Object> wrapper = new LinkedHashMap<>();
        wrapper.put("path", entry.path());
        wrapper.put("content", content);
        return json(wrapper);
    }

    private List<Map<String, Object>> asMapList(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> results = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                results.add(toStringObjectMap(map));
            }
        }
        return results;
    }

    private Map<String, Object> toStringObjectMap(Map<?, ?> rawMap) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
            if (entry.getKey() != null) {
                normalized.put(String.valueOf(entry.getKey()), entry.getValue());
            }
        }
        return normalized;
    }

    private Integer intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof String text) {
            return Boolean.parseBoolean(text.trim());
        }
        return false;
    }

    private String normalizedText(Object value) {
        if (value == null) {
            return null;
        }
        String normalized = String.valueOf(value).trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizedUpperText(Object value) {
        String text = normalizedText(value);
        return text == null ? null : text.toUpperCase(Locale.ROOT);
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String json(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize normalized asset metadata", e);
        }
    }
}
