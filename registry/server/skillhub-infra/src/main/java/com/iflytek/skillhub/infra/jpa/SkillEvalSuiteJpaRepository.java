package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.skill.SkillEvalSuite;
import com.iflytek.skillhub.domain.skill.SkillEvalSuiteRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillEvalSuiteJpaRepository extends JpaRepository<SkillEvalSuite, Long>, SkillEvalSuiteRepository {
    List<SkillEvalSuite> findBySkillVersionId(Long skillVersionId);
    Optional<SkillEvalSuite> findBySkillVersionIdAndSuiteKey(Long skillVersionId, String suiteKey);
    void deleteBySkillVersionId(Long skillVersionId);
}
