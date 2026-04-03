package com.iflytek.skillhub.domain.skill;

import java.util.List;
import java.util.Optional;

public interface SkillEnvironmentProfileRepository {
    List<SkillEnvironmentProfile> findBySkillVersionId(Long skillVersionId);
    Optional<SkillEnvironmentProfile> findBySkillVersionIdAndProfileKey(Long skillVersionId, String profileKey);
    SkillEnvironmentProfile save(SkillEnvironmentProfile profile);
    void deleteBySkillVersionId(Long skillVersionId);
}
