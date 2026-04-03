package com.iflytek.skillhub.domain.skill;

import java.util.Optional;

public interface SkillBundleArtifactRepository {
    Optional<SkillBundleArtifact> findBySkillVersionId(Long skillVersionId);
    SkillBundleArtifact save(SkillBundleArtifact artifact);
    void deleteBySkillVersionId(Long skillVersionId);
}
