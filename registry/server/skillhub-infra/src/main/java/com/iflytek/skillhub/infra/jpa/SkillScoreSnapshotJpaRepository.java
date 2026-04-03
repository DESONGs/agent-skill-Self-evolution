package com.iflytek.skillhub.infra.jpa;

import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshot;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SkillScoreSnapshotJpaRepository
        extends JpaRepository<SkillScoreSnapshot, Long>, SkillScoreSnapshotRepository {
    Optional<SkillScoreSnapshot> findBySkillId(Long skillId);

    List<SkillScoreSnapshot> findBySkillIdIn(List<Long> skillIds);

    List<SkillScoreSnapshot> findAllByOrderByUpdatedAtDesc();

    void deleteBySkillId(Long skillId);
}
