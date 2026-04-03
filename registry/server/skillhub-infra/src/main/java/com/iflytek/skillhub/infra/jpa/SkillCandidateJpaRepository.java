package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillCandidateJpaRepository extends JpaRepository<SkillCandidate, Long>, SkillCandidateRepository {
    Optional<SkillCandidate> findByCandidateKey(String candidateKey);

    List<SkillCandidate> findByPromotionState(String promotionState);

    List<SkillCandidate> findAllByOrderByUpdatedAtDesc();

    List<SkillCandidate> findByPublishedSkillIdIn(List<Long> skillIds);
}
