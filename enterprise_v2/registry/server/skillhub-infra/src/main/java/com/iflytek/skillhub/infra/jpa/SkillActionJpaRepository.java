package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.skill.SkillAction;
import com.iflytek.skillhub.domain.skill.SkillActionRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillActionJpaRepository extends JpaRepository<SkillAction, Long>, SkillActionRepository {
    List<SkillAction> findBySkillVersionId(Long skillVersionId);
    Optional<SkillAction> findBySkillVersionIdAndActionId(Long skillVersionId, String actionId);
    void deleteBySkillVersionId(Long skillVersionId);
}
