package com.iflytek.skillhub.dto;

import java.time.Instant;
import java.util.List;

public record SkillDistributionResponse(
        Long skillId,
        String namespace,
        String slug,
        String displayName,
        String summary,
        String visibility,
        boolean hidden,
        VersionDescriptor version,
        BundleDescriptor bundle,
        List<SkillLabelDto> labels,
        List<String> tags,
        List<EnvironmentProfileDescriptor> environmentProfiles,
        List<ActionDescriptor> actions,
        List<EvalSuiteDescriptor> evalSuites,
        List<FileDescriptor> files,
        List<SecurityAuditDescriptor> securityAudits
) {
    public record VersionDescriptor(
            Long id,
            String version,
            String status,
            String requestedVisibility,
            Instant publishedAt,
            int fileCount,
            long totalSize,
            boolean bundleReady,
            boolean downloadReady,
            String parsedMetadataJson,
            String manifestJson
    ) {
    }

    public record BundleDescriptor(
            String downloadPath,
            String presignedUrl,
            String contentType,
            Long contentLength,
            String filename,
            boolean fallbackBundle,
            String buildStatus,
            String sha256,
            String manifestDigest,
            Instant builtAt
    ) {
    }

    public record EnvironmentProfileDescriptor(
            Long id,
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

    public record ActionDescriptor(
            Long id,
            String actionId,
            String displayName,
            String actionKind,
            String entryPath,
            String runtimeFamily,
            Long environmentProfileId,
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

    public record EvalSuiteDescriptor(
            Long id,
            String suiteKey,
            String displayName,
            String suiteType,
            String entryPath,
            String gateLevel,
            String configJson,
            String successCriteriaJson,
            String latestReportKey
    ) {
    }

    public record FileDescriptor(
            Long id,
            String path,
            long size,
            String contentType,
            String sha256
    ) {
    }

    public record SecurityAuditDescriptor(
            Long id,
            String scanId,
            String scannerType,
            String verdict,
            Boolean safe,
            String maxSeverity,
            Integer findingsCount,
            String findingsJson,
            Double scanDurationSeconds,
            Instant scannedAt,
            Instant createdAt
    ) {
    }
}
