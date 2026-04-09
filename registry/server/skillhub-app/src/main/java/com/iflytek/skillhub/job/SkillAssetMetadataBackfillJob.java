package com.iflytek.skillhub.job;

import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillAction;
import com.iflytek.skillhub.domain.skill.SkillActionRepository;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfile;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfileRepository;
import com.iflytek.skillhub.domain.skill.SkillEvalSuite;
import com.iflytek.skillhub.domain.skill.SkillEvalSuiteRepository;
import com.iflytek.skillhub.domain.skill.SkillFile;
import com.iflytek.skillhub.domain.skill.SkillFileRepository;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVersionRepository;
import com.iflytek.skillhub.domain.skill.service.SkillAssetNormalizationService;
import com.iflytek.skillhub.domain.skill.validation.PackageEntry;
import com.iflytek.skillhub.storage.ObjectStorageService;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class SkillAssetMetadataBackfillJob {

    private final SkillRepository skillRepository;
    private final SkillVersionRepository skillVersionRepository;
    private final SkillFileRepository skillFileRepository;
    private final SkillActionRepository skillActionRepository;
    private final SkillEnvironmentProfileRepository skillEnvironmentProfileRepository;
    private final SkillEvalSuiteRepository skillEvalSuiteRepository;
    private final SkillAssetNormalizationService skillAssetNormalizationService;
    private final ObjectStorageService objectStorageService;

    public SkillAssetMetadataBackfillJob(SkillRepository skillRepository,
                                         SkillVersionRepository skillVersionRepository,
                                         SkillFileRepository skillFileRepository,
                                         SkillActionRepository skillActionRepository,
                                         SkillEnvironmentProfileRepository skillEnvironmentProfileRepository,
                                         SkillEvalSuiteRepository skillEvalSuiteRepository,
                                         SkillAssetNormalizationService skillAssetNormalizationService,
                                         ObjectStorageService objectStorageService) {
        this.skillRepository = skillRepository;
        this.skillVersionRepository = skillVersionRepository;
        this.skillFileRepository = skillFileRepository;
        this.skillActionRepository = skillActionRepository;
        this.skillEnvironmentProfileRepository = skillEnvironmentProfileRepository;
        this.skillEvalSuiteRepository = skillEvalSuiteRepository;
        this.skillAssetNormalizationService = skillAssetNormalizationService;
        this.objectStorageService = objectStorageService;
    }

    @Transactional
    public void backfillAll() {
        for (Skill skill : skillRepository.findAll()) {
            for (SkillVersion version : skillVersionRepository.findBySkillId(skill.getId())) {
                if (!skillActionRepository.findBySkillVersionId(version.getId()).isEmpty()
                        || !skillEnvironmentProfileRepository.findBySkillVersionId(version.getId()).isEmpty()
                        || !skillEvalSuiteRepository.findBySkillVersionId(version.getId()).isEmpty()) {
                    continue;
                }
                backfillVersion(version);
            }
        }
    }

    private void backfillVersion(SkillVersion version) {
        List<PackageEntry> entries = skillFileRepository.findByVersionId(version.getId()).stream()
                .map(this::toPackageEntry)
                .toList();
        SkillAssetNormalizationService.AssetNormalizationResult normalized =
                skillAssetNormalizationService.normalize(entries);
        java.util.Map<String, Long> environmentProfileIdsByKey = new java.util.HashMap<>();

        skillEnvironmentProfileRepository.deleteBySkillVersionId(version.getId());
        skillActionRepository.deleteBySkillVersionId(version.getId());
        skillEvalSuiteRepository.deleteBySkillVersionId(version.getId());

        normalized.environmentProfiles().forEach(profile -> {
            SkillEnvironmentProfile entity = new SkillEnvironmentProfile(version.getId(), profile.profileKey(), "backfill");
            entity.setDisplayName(profile.displayName());
            entity.setRuntimeFamily(profile.runtimeFamily());
            entity.setRuntimeVersionRange(profile.runtimeVersionRange());
            entity.setToolRequirementsJson(profile.toolRequirementsJson());
            entity.setCapabilityTagsJson(profile.capabilityTagsJson());
            entity.setOsConstraintsJson(profile.osConstraintsJson());
            entity.setNetworkPolicy(profile.networkPolicy());
            entity.setFilesystemPolicy(profile.filesystemPolicy());
            entity.setSandboxMode(profile.sandboxMode());
            entity.setResourceLimitsJson(profile.resourceLimitsJson());
            entity.setEnvSchemaJson(profile.envSchemaJson());
            entity.setDefaultProfile(profile.defaultProfile());
            SkillEnvironmentProfile saved = skillEnvironmentProfileRepository.save(entity);
            environmentProfileIdsByKey.put(profile.profileKey(), saved.getId());
        });

        normalized.actions().forEach(action -> {
            SkillAction entity = new SkillAction(version.getId(), action.actionId(), action.actionKind(), action.entryPath(), "backfill");
            entity.setDisplayName(action.displayName());
            entity.setRuntimeFamily(action.runtimeFamily());
            entity.setEnvironmentProfileId(environmentProfileIdsByKey.get(action.environmentProfileKey()));
            entity.setTimeoutSec(action.timeoutSec());
            entity.setSandboxMode(action.sandboxMode());
            entity.setAllowNetwork(action.allowNetwork());
            entity.setInputSchemaJson(action.inputSchemaJson());
            entity.setOutputSchemaJson(action.outputSchemaJson());
            entity.setSideEffectsJson(action.sideEffectsJson());
            entity.setIdempotencyMode(action.idempotencyMode());
            entity.setDefaultAction(action.defaultAction());
            skillActionRepository.save(entity);
        });

        normalized.evalSuites().forEach(suite -> {
            SkillEvalSuite entity = new SkillEvalSuite(version.getId(), suite.suiteKey(), suite.suiteType(), suite.gateLevel(), "backfill");
            entity.setDisplayName(suite.displayName());
            entity.setEntryPath(suite.entryPath());
            entity.setConfigJson(suite.configJson());
            entity.setSuccessCriteriaJson(suite.successCriteriaJson());
            skillEvalSuiteRepository.save(entity);
        });
    }

    private PackageEntry toPackageEntry(SkillFile file) {
        try (InputStream inputStream = objectStorageService.getObject(file.getStorageKey())) {
            byte[] bytes = inputStream.readAllBytes();
            return new PackageEntry(
                    file.getFilePath(),
                    bytes,
                    bytes.length,
                    file.getContentType()
            );
        } catch (IOException ex) {
            throw new IllegalStateException("Failed to read skill file for backfill: " + file.getStorageKey(), ex);
        }
    }
}
