package com.iflytek.skillhub.service;

import com.iflytek.skillhub.domain.namespace.NamespaceRole;
import com.iflytek.skillhub.domain.security.SecurityAudit;
import com.iflytek.skillhub.domain.security.SecurityAuditRepository;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillAction;
import com.iflytek.skillhub.domain.skill.SkillActionRepository;
import com.iflytek.skillhub.domain.skill.SkillBundleArtifact;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfile;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfileRepository;
import com.iflytek.skillhub.domain.skill.SkillEvalSuite;
import com.iflytek.skillhub.domain.skill.SkillEvalSuiteRepository;
import com.iflytek.skillhub.domain.skill.SkillFile;
import com.iflytek.skillhub.domain.skill.SkillFileRepository;
import com.iflytek.skillhub.domain.skill.SkillTag;
import com.iflytek.skillhub.domain.skill.SkillTagRepository;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.service.SkillDownloadService;
import com.iflytek.skillhub.dto.SkillDistributionResponse;
import com.iflytek.skillhub.dto.internal.InternalSkillDistributionResponse;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Service;

@Service
public class SkillDistributionAppService {

    private final SkillDownloadService skillDownloadService;
    private final SkillFileRepository skillFileRepository;
    private final SkillTagRepository skillTagRepository;
    private final SkillEnvironmentProfileRepository skillEnvironmentProfileRepository;
    private final SkillActionRepository skillActionRepository;
    private final SkillEvalSuiteRepository skillEvalSuiteRepository;
    private final SecurityAuditRepository securityAuditRepository;
    private final SkillLabelAppService skillLabelAppService;

    public SkillDistributionAppService(
            SkillDownloadService skillDownloadService,
            SkillFileRepository skillFileRepository,
            SkillTagRepository skillTagRepository,
            SkillEnvironmentProfileRepository skillEnvironmentProfileRepository,
            SkillActionRepository skillActionRepository,
            SkillEvalSuiteRepository skillEvalSuiteRepository,
            SecurityAuditRepository securityAuditRepository,
            SkillLabelAppService skillLabelAppService) {
        this.skillDownloadService = skillDownloadService;
        this.skillFileRepository = skillFileRepository;
        this.skillTagRepository = skillTagRepository;
        this.skillEnvironmentProfileRepository = skillEnvironmentProfileRepository;
        this.skillActionRepository = skillActionRepository;
        this.skillEvalSuiteRepository = skillEvalSuiteRepository;
        this.securityAuditRepository = securityAuditRepository;
        this.skillLabelAppService = skillLabelAppService;
    }

    public SkillDistributionResponse getLatestDistribution(
            String namespace,
            String slug,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor = resolveLatestDistribution(namespace, slug, userId, userNsRoles);
        return toPublicResponse(descriptor, namespace, buildLatestDownloadPath(namespace, slug));
    }

    public SkillDistributionResponse getVersionDistribution(
            String namespace,
            String slug,
            String version,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor =
                resolveVersionDistribution(namespace, slug, version, userId, userNsRoles);
        return toPublicResponse(descriptor, namespace, buildVersionDownloadPath(namespace, slug, version));
    }

    public SkillDistributionResponse getTagDistribution(
            String namespace,
            String slug,
            String tagName,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor =
                resolveTagDistribution(namespace, slug, tagName, userId, userNsRoles);
        return toPublicResponse(descriptor, namespace, buildTagDownloadPath(namespace, slug, tagName));
    }

    public InternalSkillDistributionResponse getLatestInternalDistribution(
            String namespace,
            String slug,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor = resolveLatestDistribution(namespace, slug, userId, userNsRoles);
        return toInternalResponse(descriptor, namespace, buildLatestDownloadPath(namespace, slug));
    }

    public InternalSkillDistributionResponse getVersionInternalDistribution(
            String namespace,
            String slug,
            String version,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor =
                resolveVersionDistribution(namespace, slug, version, userId, userNsRoles);
        return toInternalResponse(descriptor, namespace, buildVersionDownloadPath(namespace, slug, version));
    }

    public InternalSkillDistributionResponse getTagInternalDistribution(
            String namespace,
            String slug,
            String tagName,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        SkillDownloadService.DistributionDescriptor descriptor =
                resolveTagDistribution(namespace, slug, tagName, userId, userNsRoles);
        return toInternalResponse(descriptor, namespace, buildTagDownloadPath(namespace, slug, tagName));
    }

    private SkillDownloadService.DistributionDescriptor resolveLatestDistribution(
            String namespace,
            String slug,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        return skillDownloadService.describeLatest(namespace, slug, userId, normalizeRoles(userNsRoles));
    }

    private SkillDownloadService.DistributionDescriptor resolveVersionDistribution(
            String namespace,
            String slug,
            String version,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        return skillDownloadService.describeVersion(namespace, slug, version, userId, normalizeRoles(userNsRoles));
    }

    private SkillDownloadService.DistributionDescriptor resolveTagDistribution(
            String namespace,
            String slug,
            String tagName,
            String userId,
            Map<Long, NamespaceRole> userNsRoles) {
        return skillDownloadService.describeByTag(namespace, slug, tagName, userId, normalizeRoles(userNsRoles));
    }

    private SkillDistributionResponse toPublicResponse(
            SkillDownloadService.DistributionDescriptor descriptor,
            String namespace,
            String downloadPath) {
        Skill skill = descriptor.skill();
        SkillVersion version = descriptor.version();
        Long versionId = version.getId();

        return new SkillDistributionResponse(
                skill.getId(),
                namespace,
                skill.getSlug(),
                skill.getDisplayName(),
                skill.getSummary(),
                skill.getVisibility().name(),
                skill.isHidden(),
                toVersionDescriptor(version),
                toPublicBundleDescriptor(descriptor.bundle(), downloadPath),
                skillLabelAppService.listSkillLabelsBySkillId(skill.getId()),
                versionTags(skill.getId(), versionId),
                environmentProfiles(versionId),
                actions(versionId),
                evalSuites(versionId),
                publicFiles(versionId),
                securityAudits(versionId)
        );
    }

    private InternalSkillDistributionResponse toInternalResponse(
            SkillDownloadService.DistributionDescriptor descriptor,
            String namespace,
            String downloadPath) {
        Skill skill = descriptor.skill();
        SkillVersion version = descriptor.version();
        Long versionId = version.getId();

        return new InternalSkillDistributionResponse(
                skill.getId(),
                namespace,
                skill.getSlug(),
                skill.getDisplayName(),
                skill.getSummary(),
                skill.getVisibility().name(),
                skill.isHidden(),
                toVersionDescriptor(version),
                toInternalBundleDescriptor(descriptor.bundle(), downloadPath),
                skillLabelAppService.listSkillLabelsBySkillId(skill.getId()),
                versionTags(skill.getId(), versionId),
                environmentProfiles(versionId),
                actions(versionId),
                evalSuites(versionId),
                internalFiles(versionId),
                securityAudits(versionId)
        );
    }

    private SkillDistributionResponse.VersionDescriptor toVersionDescriptor(SkillVersion version) {
        return new SkillDistributionResponse.VersionDescriptor(
                version.getId(),
                version.getVersion(),
                version.getStatus().name(),
                version.getRequestedVisibility() != null ? version.getRequestedVisibility().name() : null,
                version.getPublishedAt(),
                version.getFileCount(),
                version.getTotalSize(),
                version.isBundleReady(),
                version.isDownloadReady(),
                version.getParsedMetadataJson(),
                version.getManifestJson()
        );
    }

    private SkillDistributionResponse.BundleDescriptor toPublicBundleDescriptor(
            SkillDownloadService.BundleAccessDescriptor bundle,
            String downloadPath) {
        SkillBundleArtifact artifact = bundle.artifact();
        String buildStatus = artifact != null
                ? artifact.getBuildStatus()
                : (bundle.fallbackBundle() ? "FALLBACK_ZIP" : "READY");
        return new SkillDistributionResponse.BundleDescriptor(
                downloadPath,
                bundle.presignedUrl(),
                bundle.contentType(),
                bundle.contentLength(),
                bundle.filename(),
                bundle.fallbackBundle(),
                buildStatus,
                artifact != null ? artifact.getSha256() : null,
                artifact != null ? artifact.getManifestDigest() : null,
                artifact != null ? artifact.getBuiltAt() : null
        );
    }

    private InternalSkillDistributionResponse.InternalBundleDescriptor toInternalBundleDescriptor(
            SkillDownloadService.BundleAccessDescriptor bundle,
            String downloadPath) {
        SkillBundleArtifact artifact = bundle.artifact();
        String buildStatus = artifact != null
                ? artifact.getBuildStatus()
                : (bundle.fallbackBundle() ? "FALLBACK_ZIP" : "READY");
        return new InternalSkillDistributionResponse.InternalBundleDescriptor(
                downloadPath,
                bundle.presignedUrl(),
                bundle.storageKey(),
                bundle.contentType(),
                bundle.contentLength(),
                bundle.filename(),
                bundle.fallbackBundle(),
                buildStatus,
                artifact != null ? artifact.getSha256() : null,
                artifact != null ? artifact.getManifestDigest() : null,
                artifact != null ? artifact.getBuiltAt() : null
        );
    }

    private List<String> versionTags(Long skillId, Long versionId) {
        return skillTagRepository.findBySkillId(skillId).stream()
                .filter(tag -> Objects.equals(tag.getVersionId(), versionId))
                .map(SkillTag::getTagName)
                .sorted()
                .toList();
    }

    private List<SkillDistributionResponse.EnvironmentProfileDescriptor> environmentProfiles(Long versionId) {
        return skillEnvironmentProfileRepository.findBySkillVersionId(versionId).stream()
                .sorted(Comparator.comparing(SkillEnvironmentProfile::getProfileKey))
                .map(profile -> new SkillDistributionResponse.EnvironmentProfileDescriptor(
                        profile.getId(),
                        profile.getProfileKey(),
                        profile.getDisplayName(),
                        profile.getRuntimeFamily(),
                        profile.getRuntimeVersionRange(),
                        profile.getToolRequirementsJson(),
                        profile.getCapabilityTagsJson(),
                        profile.getOsConstraintsJson(),
                        profile.getNetworkPolicy(),
                        profile.getFilesystemPolicy(),
                        profile.getSandboxMode(),
                        profile.getResourceLimitsJson(),
                        profile.getEnvSchemaJson(),
                        profile.isDefaultProfile()
                ))
                .toList();
    }

    private List<SkillDistributionResponse.ActionDescriptor> actions(Long versionId) {
        return skillActionRepository.findBySkillVersionId(versionId).stream()
                .sorted(Comparator.comparing(SkillAction::getActionId))
                .map(action -> new SkillDistributionResponse.ActionDescriptor(
                        action.getId(),
                        action.getActionId(),
                        action.getDisplayName(),
                        action.getActionKind(),
                        action.getEntryPath(),
                        action.getRuntimeFamily(),
                        action.getEnvironmentProfileId(),
                        action.getTimeoutSec(),
                        action.getSandboxMode(),
                        action.isAllowNetwork(),
                        action.getInputSchemaJson(),
                        action.getOutputSchemaJson(),
                        action.getSideEffectsJson(),
                        action.getIdempotencyMode(),
                        action.isDefaultAction()
                ))
                .toList();
    }

    private List<SkillDistributionResponse.EvalSuiteDescriptor> evalSuites(Long versionId) {
        return skillEvalSuiteRepository.findBySkillVersionId(versionId).stream()
                .sorted(Comparator.comparing(SkillEvalSuite::getSuiteKey))
                .map(suite -> new SkillDistributionResponse.EvalSuiteDescriptor(
                        suite.getId(),
                        suite.getSuiteKey(),
                        suite.getDisplayName(),
                        suite.getSuiteType(),
                        suite.getEntryPath(),
                        suite.getGateLevel(),
                        suite.getConfigJson(),
                        suite.getSuccessCriteriaJson(),
                        suite.getLatestReportKey()
                ))
                .toList();
    }

    private List<SkillDistributionResponse.FileDescriptor> publicFiles(Long versionId) {
        return skillFileRepository.findByVersionId(versionId).stream()
                .sorted(Comparator.comparing(SkillFile::getFilePath))
                .map(file -> new SkillDistributionResponse.FileDescriptor(
                        file.getId(),
                        file.getFilePath(),
                        file.getFileSize(),
                        file.getContentType(),
                        file.getSha256()
                ))
                .toList();
    }

    private List<InternalSkillDistributionResponse.InternalFileDescriptor> internalFiles(Long versionId) {
        return skillFileRepository.findByVersionId(versionId).stream()
                .sorted(Comparator.comparing(SkillFile::getFilePath))
                .map(file -> new InternalSkillDistributionResponse.InternalFileDescriptor(
                        file.getId(),
                        file.getFilePath(),
                        file.getFileSize(),
                        file.getContentType(),
                        file.getSha256(),
                        file.getStorageKey()
                ))
                .toList();
    }

    private List<SkillDistributionResponse.SecurityAuditDescriptor> securityAudits(Long versionId) {
        return securityAuditRepository.findLatestActiveByVersionId(versionId).stream()
                .sorted(Comparator.comparing(SecurityAudit::getScannedAt, Comparator.nullsLast(Comparator.reverseOrder()))
                        .thenComparing(SecurityAudit::getCreatedAt, Comparator.reverseOrder()))
                .map(audit -> new SkillDistributionResponse.SecurityAuditDescriptor(
                        audit.getId(),
                        audit.getScanId(),
                        audit.getScannerType().name(),
                        audit.getVerdict().name(),
                        audit.getIsSafe(),
                        audit.getMaxSeverity(),
                        audit.getFindingsCount(),
                        audit.getFindings(),
                        audit.getScanDurationSeconds(),
                        audit.getScannedAt(),
                        audit.getCreatedAt()
                ))
                .toList();
    }

    private Map<Long, NamespaceRole> normalizeRoles(Map<Long, NamespaceRole> userNsRoles) {
        return userNsRoles != null ? userNsRoles : Map.of();
    }

    private String buildLatestDownloadPath(String namespace, String slug) {
        return "/api/v1/skills/" + encode(namespace) + "/" + encode(slug) + "/download";
    }

    private String buildVersionDownloadPath(String namespace, String slug, String version) {
        return "/api/v1/skills/" + encode(namespace) + "/" + encode(slug)
                + "/versions/" + encode(version) + "/download";
    }

    private String buildTagDownloadPath(String namespace, String slug, String tagName) {
        return "/api/v1/skills/" + encode(namespace) + "/" + encode(slug)
                + "/tags/" + encode(tagName) + "/download";
    }

    private String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }
}
