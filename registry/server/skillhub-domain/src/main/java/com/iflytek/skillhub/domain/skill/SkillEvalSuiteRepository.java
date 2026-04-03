package com.iflytek.skillhub.domain.skill;

import java.util.List;
import java.util.Optional;

public interface SkillEvalSuiteRepository {
    List<SkillEvalSuite> findBySkillVersionId(Long skillVersionId);
    Optional<SkillEvalSuite> findBySkillVersionIdAndSuiteKey(Long skillVersionId, String suiteKey);
    SkillEvalSuite save(SkillEvalSuite suite);
    void deleteBySkillVersionId(Long skillVersionId);
}
