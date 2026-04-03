package com.iflytek.skillhub.domain.feedback;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface SkillRunFeedbackRepository {
    Optional<SkillRunFeedback> findByDedupeKey(String dedupeKey);

    List<SkillRunFeedback> findBySkillId(Long skillId);

    List<SkillRunFeedback> findBySkillVersionId(Long skillVersionId);

    List<SkillRunFeedback> findByObservedAtGreaterThanEqual(Instant observedAt);

    List<SkillRunFeedback> findBySkillIdAndObservedAtGreaterThanEqual(Long skillId, Instant observedAt);

    List<SkillRunFeedback> findBySkillIdInAndObservedAtGreaterThanEqual(List<Long> skillIds, Instant observedAt);

    List<SkillRunFeedback> findBySkillCandidateId(Long skillCandidateId);

    List<SkillRunFeedback> findBySkillCandidateIdInAndObservedAtGreaterThanEqual(List<Long> candidateIds, Instant observedAt);

    SkillRunFeedback save(SkillRunFeedback feedback);
}
