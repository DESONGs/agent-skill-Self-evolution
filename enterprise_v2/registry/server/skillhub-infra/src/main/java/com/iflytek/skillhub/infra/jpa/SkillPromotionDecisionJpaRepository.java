package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.candidate.SkillPromotionDecision;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecisionRepository;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillPromotionDecisionJpaRepository
        extends JpaRepository<SkillPromotionDecision, Long>, SkillPromotionDecisionRepository {
    List<SkillPromotionDecision> findBySkillCandidateId(Long skillCandidateId);

    List<SkillPromotionDecision> findBySkillCandidateIdOrderByDecidedAtDesc(Long skillCandidateId);

    List<SkillPromotionDecision> findBySkillCandidateIdIn(List<Long> skillCandidateIds);
}
