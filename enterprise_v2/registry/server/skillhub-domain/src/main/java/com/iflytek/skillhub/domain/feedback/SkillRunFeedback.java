package com.iflytek.skillhub.domain.feedback;

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
@Table(name = "skill_run_feedback")
public class SkillRunFeedback {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "dedupe_key", nullable = false, length = 128, unique = true)
    private String dedupeKey;

    @Column(name = "feedback_source", nullable = false, length = 32)
    private String feedbackSource;

    @Column(name = "subject_type", nullable = false, length = 32)
    private String subjectType;

    @Column(name = "skill_id")
    private Long skillId;

    @Column(name = "skill_version_id")
    private Long skillVersionId;

    @Column(name = "skill_action_id")
    private Long skillActionId;

    @Column(name = "skill_candidate_id")
    private Long skillCandidateId;

    @Column(name = "environment_profile_id")
    private Long environmentProfileId;

    @Column(name = "source_run_id", length = 128)
    private String sourceRunId;

    @Column(name = "feedback_type", nullable = false, length = 32)
    private String feedbackType;

    @Column
    private Boolean success;

    @Column
    private Integer rating;

    @Column(name = "latency_ms")
    private Long latencyMs;

    @Column(name = "error_code", length = 128)
    private String errorCode;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload_json", columnDefinition = "jsonb", nullable = false)
    private String payloadJson = "{}";

    @Column(name = "observed_at")
    private Instant observedAt;

    @Column(name = "ingested_at", nullable = false, updatable = false)
    private Instant ingestedAt;

    @Column(name = "actor_id", length = 128)
    private String actorId;

    protected SkillRunFeedback() {
    }

    public SkillRunFeedback(String dedupeKey,
                            String feedbackSource,
                            String subjectType,
                            Long skillId,
                            Long skillVersionId,
                            Long skillActionId,
                            Long skillCandidateId,
                            Long environmentProfileId,
                            String sourceRunId,
                            String feedbackType,
                            Boolean success,
                            Integer rating,
                            Long latencyMs,
                            String errorCode,
                            String payloadJson,
                            Instant observedAt,
                            String actorId) {
        this.dedupeKey = dedupeKey;
        this.feedbackSource = feedbackSource;
        this.subjectType = subjectType;
        this.skillId = skillId;
        this.skillVersionId = skillVersionId;
        this.skillActionId = skillActionId;
        this.skillCandidateId = skillCandidateId;
        this.environmentProfileId = environmentProfileId;
        this.sourceRunId = sourceRunId;
        this.feedbackType = feedbackType;
        this.success = success;
        this.rating = rating;
        this.latencyMs = latencyMs;
        this.errorCode = errorCode;
        this.payloadJson = payloadJson;
        this.observedAt = observedAt;
        this.actorId = actorId;
    }

    @PrePersist
    protected void onCreate() {
        Instant now = Instant.now(Clock.systemUTC());
        ingestedAt = now;
        if (observedAt == null) {
            observedAt = now;
        }
    }

    public Long getId() {
        return id;
    }

    public String getDedupeKey() {
        return dedupeKey;
    }

    public String getFeedbackSource() {
        return feedbackSource;
    }

    public String getSubjectType() {
        return subjectType;
    }

    public Long getSkillId() {
        return skillId;
    }

    public Long getSkillVersionId() {
        return skillVersionId;
    }

    public Long getSkillActionId() {
        return skillActionId;
    }

    public Long getSkillCandidateId() {
        return skillCandidateId;
    }

    public Long getEnvironmentProfileId() {
        return environmentProfileId;
    }

    public String getSourceRunId() {
        return sourceRunId;
    }

    public String getFeedbackType() {
        return feedbackType;
    }

    public Boolean getSuccess() {
        return success;
    }

    public Integer getRating() {
        return rating;
    }

    public Long getLatencyMs() {
        return latencyMs;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public String getPayloadJson() {
        return payloadJson;
    }

    public Instant getObservedAt() {
        return observedAt;
    }

    public Instant getIngestedAt() {
        return ingestedAt;
    }

    public String getActorId() {
        return actorId;
    }
}

