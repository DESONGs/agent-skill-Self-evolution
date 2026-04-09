package com.iflytek.skillhub.domain.feedback;

import java.util.List;
import java.util.Optional;

public interface SkillScoreSnapshotRepository {
    Optional<SkillScoreSnapshot> findBySkillId(Long skillId);

    List<SkillScoreSnapshot> findBySkillIdIn(List<Long> skillIds);

    List<SkillScoreSnapshot> findAllByOrderByUpdatedAtDesc();

    SkillScoreSnapshot save(SkillScoreSnapshot snapshot);

    void deleteBySkillId(Long skillId);
}
