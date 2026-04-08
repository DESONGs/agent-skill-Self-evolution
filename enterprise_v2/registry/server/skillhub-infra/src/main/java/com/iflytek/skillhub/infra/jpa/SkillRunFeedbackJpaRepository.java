package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.feedback.SkillRunFeedback;
import com.iflytek.skillhub.domain.feedback.SkillRunFeedbackRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillRunFeedbackJpaRepository extends JpaRepository<SkillRunFeedback, Long>, SkillRunFeedbackRepository {
    Optional<SkillRunFeedback> findByDedupeKey(String dedupeKey);

    List<SkillRunFeedback> findBySkillId(Long skillId);

    List<SkillRunFeedback> findBySkillVersionId(Long skillVersionId);

    List<SkillRunFeedback> findByObservedAtGreaterThanEqual(Instant observedAt);

    List<SkillRunFeedback> findBySkillIdAndObservedAtGreaterThanEqual(Long skillId, Instant observedAt);

    List<SkillRunFeedback> findBySkillIdInAndObservedAtGreaterThanEqual(List<Long> skillIds, Instant observedAt);

    List<SkillRunFeedback> findBySkillCandidateId(Long skillCandidateId);

    List<SkillRunFeedback> findBySkillCandidateIdInAndObservedAtGreaterThanEqual(List<Long> candidateIds, Instant observedAt);
}
