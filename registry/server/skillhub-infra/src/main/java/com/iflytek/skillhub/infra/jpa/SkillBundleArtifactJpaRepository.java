package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.skill.SkillBundleArtifact;
import com.iflytek.skillhub.domain.skill.SkillBundleArtifactRepository;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillBundleArtifactJpaRepository
        extends JpaRepository<SkillBundleArtifact, Long>, SkillBundleArtifactRepository {
    Optional<SkillBundleArtifact> findBySkillVersionId(Long skillVersionId);
    void deleteBySkillVersionId(Long skillVersionId);
}
