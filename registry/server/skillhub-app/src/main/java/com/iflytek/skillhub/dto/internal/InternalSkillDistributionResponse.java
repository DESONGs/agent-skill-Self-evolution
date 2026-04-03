package com.iflytek.skillhub.dto.internal;

import com.iflytek.skillhub.dto.SkillDistributionResponse;
import com.iflytek.skillhub.dto.SkillLabelDto;
import java.util.List;

public record InternalSkillDistributionResponse(
        Long skillId,
        String namespace,
        String slug,
        String displayName,
        String summary,
        String visibility,
        boolean hidden,
        SkillDistributionResponse.VersionDescriptor version,
        InternalBundleDescriptor bundle,
        List<SkillLabelDto> labels,
        List<String> tags,
        List<SkillDistributionResponse.EnvironmentProfileDescriptor> environmentProfiles,
        List<SkillDistributionResponse.ActionDescriptor> actions,
        List<SkillDistributionResponse.EvalSuiteDescriptor> evalSuites,
        List<InternalFileDescriptor> files,
        List<SkillDistributionResponse.SecurityAuditDescriptor> securityAudits
) {
    public record InternalBundleDescriptor(
            String downloadPath,
            String presignedUrl,
            String storageKey,
            String contentType,
            Long contentLength,
            String filename,
            boolean fallbackBundle,
            String buildStatus,
            String sha256,
            String manifestDigest,
            java.time.Instant builtAt
    ) {
    }

    public record InternalFileDescriptor(
            Long id,
            String path,
            long size,
            String contentType,
            String sha256,
            String storageKey
    ) {
    }
}
