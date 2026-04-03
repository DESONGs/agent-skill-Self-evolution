package com.iflytek.skillhub.domain.skill;

import java.util.List;
import java.util.Optional;

public interface SkillActionRepository {
    List<SkillAction> findBySkillVersionId(Long skillVersionId);
    Optional<SkillAction> findBySkillVersionIdAndActionId(Long skillVersionId, String actionId);
    SkillAction save(SkillAction action);
    void deleteBySkillVersionId(Long skillVersionId);
}
