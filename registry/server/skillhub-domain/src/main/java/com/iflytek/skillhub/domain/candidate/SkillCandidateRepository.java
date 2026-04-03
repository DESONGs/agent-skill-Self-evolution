package com.iflytek.skillhub.domain.candidate;

import java.util.List;
import java.util.Optional;

public interface SkillCandidateRepository {
    Optional<SkillCandidate> findById(Long id);

    Optional<SkillCandidate> findByCandidateKey(String candidateKey);

    List<SkillCandidate> findByPromotionState(String promotionState);

    List<SkillCandidate> findAllByOrderByUpdatedAtDesc();

    List<SkillCandidate> findByPublishedSkillIdIn(List<Long> skillIds);

    SkillCandidate save(SkillCandidate candidate);
}
