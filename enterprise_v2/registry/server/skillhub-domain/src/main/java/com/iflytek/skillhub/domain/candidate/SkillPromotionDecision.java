package com.iflytek.skillhub.domain.candidate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Clock;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "skill_promotion_decision")
public class SkillPromotionDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_candidate_id", nullable = false)
    private Long skillCandidateId;

    @Column(nullable = false, length = 32)
    private String decision;

    @Column(name = "decision_mode", nullable = false, length = 32)
    private String decisionMode;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "reasons_json", columnDefinition = "jsonb", nullable = false)
    private String reasonsJson = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "scores_json", columnDefinition = "jsonb", nullable = false)
    private String scoresJson = "{}";

    @Column(name = "evidence_index_key", length = 512)
    private String evidenceIndexKey;

    @Column(name = "decided_by", length = 128)
    private String decidedBy;

    @Column(name = "decided_at", nullable = false)
    private Instant decidedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    protected SkillPromotionDecision() {
    }

    public SkillPromotionDecision(Long skillCandidateId,
                                  String decision,
                                  String decisionMode,
                                  String reasonsJson,
                                  String scoresJson,
                                  String evidenceIndexKey,
                                  String decidedBy,
                                  Instant decidedAt) {
        this.skillCandidateId = skillCandidateId;
        this.decision = decision;
        this.decisionMode = decisionMode;
        this.reasonsJson = reasonsJson;
        this.scoresJson = scoresJson;
        this.evidenceIndexKey = evidenceIndexKey;
        this.decidedBy = decidedBy;
        this.decidedAt = decidedAt;
    }

    @PrePersist
    protected void onCreate() {
        Instant now = Instant.now(Clock.systemUTC());
        createdAt = now;
        if (decidedAt == null) {
            decidedAt = now;
        }
    }

    public Long getId() {
        return id;
    }

    public Long getSkillCandidateId() {
        return skillCandidateId;
    }

    public String getDecision() {
        return decision;
    }

    public String getDecisionMode() {
        return decisionMode;
    }

    public String getReasonsJson() {
        return reasonsJson;
    }

    public String getScoresJson() {
        return scoresJson;
    }

    public String getEvidenceIndexKey() {
        return evidenceIndexKey;
    }

    public String getDecidedBy() {
        return decidedBy;
    }

    public Instant getDecidedAt() {
        return decidedAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

