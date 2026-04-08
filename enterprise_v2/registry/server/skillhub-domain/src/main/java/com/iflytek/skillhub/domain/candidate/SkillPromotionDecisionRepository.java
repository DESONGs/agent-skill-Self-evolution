package com.iflytek.skillhub.domain.candidate;

import java.util.List;

public interface SkillPromotionDecisionRepository {
    List<SkillPromotionDecision> findBySkillCandidateId(Long skillCandidateId);

    List<SkillPromotionDecision> findBySkillCandidateIdOrderByDecidedAtDesc(Long skillCandidateId);

    List<SkillPromotionDecision> findBySkillCandidateIdIn(List<Long> skillCandidateIds);

    SkillPromotionDecision save(SkillPromotionDecision decision);
}
