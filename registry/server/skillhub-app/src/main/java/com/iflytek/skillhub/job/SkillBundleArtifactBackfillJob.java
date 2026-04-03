package com.iflytek.skillhub.job;

import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillBundleArtifact;
import com.iflytek.skillhub.domain.skill.SkillBundleArtifactRepository;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVersionRepository;
import com.iflytek.skillhub.storage.ObjectMetadata;
import com.iflytek.skillhub.storage.ObjectStorageService;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class SkillBundleArtifactBackfillJob {

    private final SkillRepository skillRepository;
    private final SkillVersionRepository skillVersionRepository;
    private final SkillBundleArtifactRepository skillBundleArtifactRepository;
    private final ObjectStorageService objectStorageService;

    public SkillBundleArtifactBackfillJob(SkillRepository skillRepository,
                                          SkillVersionRepository skillVersionRepository,
                                          SkillBundleArtifactRepository skillBundleArtifactRepository,
                                          ObjectStorageService objectStorageService) {
        this.skillRepository = skillRepository;
        this.skillVersionRepository = skillVersionRepository;
        this.skillBundleArtifactRepository = skillBundleArtifactRepository;
        this.objectStorageService = objectStorageService;
    }

    @Transactional
    public void backfillAll() {
        for (Skill skill : skillRepository.findAll()) {
            for (SkillVersion version : skillVersionRepository.findBySkillId(skill.getId())) {
                skillBundleArtifactRepository.findBySkillVersionId(version.getId()).ifPresentOrElse(
                        existing -> {
                        },
                        () -> maybeBackfill(version));
            }
        }
    }

    private void maybeBackfill(SkillVersion version) {
        String bundleKey = "packages/%d/%d/bundle.zip".formatted(version.getSkillId(), version.getId());
        if (!objectStorageService.exists(bundleKey)) {
            return;
        }
        ObjectMetadata metadata = objectStorageService.getMetadata(bundleKey);
        SkillBundleArtifact artifact = new SkillBundleArtifact(
                version.getId(),
                bundleKey,
                metadata != null ? metadata.contentType() : "application/zip",
                null,
                metadata != null ? metadata.size() : 0L,
                "READY",
                "backfill"
        );
        artifact.setBuiltAt(version.getPublishedAt());
        artifact.setManifestDigest(sha256(version.getManifestJson()));
        skillBundleArtifactRepository.save(artifact);
    }

    private String sha256(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to compute manifest digest", ex);
        }
    }
}
