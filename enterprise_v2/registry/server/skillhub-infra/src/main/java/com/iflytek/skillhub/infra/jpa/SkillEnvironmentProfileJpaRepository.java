package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfile;
import com.iflytek.skillhub.domain.skill.SkillEnvironmentProfileRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillEnvironmentProfileJpaRepository
        extends JpaRepository<SkillEnvironmentProfile, Long>, SkillEnvironmentProfileRepository {
    List<SkillEnvironmentProfile> findBySkillVersionId(Long skillVersionId);
    Optional<SkillEnvironmentProfile> findBySkillVersionIdAndProfileKey(Long skillVersionId, String profileKey);
    void deleteBySkillVersionId(Long skillVersionId);
}
