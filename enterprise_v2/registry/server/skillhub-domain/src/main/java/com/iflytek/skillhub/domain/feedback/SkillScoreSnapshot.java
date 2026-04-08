package com.iflytek.skillhub.domain.feedback;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;

@Entity
@Table(name = "skill_score_snapshot")
public class SkillScoreSnapshot {

    @Id
    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(name = "latest_published_version_id")
    private Long latestPublishedVersionId;

    @Column(name = "trust_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal trustScore = BigDecimal.ZERO;

    @Column(name = "quality_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal qualityScore = BigDecimal.ZERO;

    @Column(name = "feedback_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal feedbackScore = BigDecimal.ZERO;

    @Column(name = "success_rate_30d", precision = 10, scale = 4, nullable = false)
    private BigDecimal successRate30d = BigDecimal.ZERO;

    @Column(name = "rating_bayes", precision = 10, scale = 4, nullable = false)
    private BigDecimal ratingBayes = BigDecimal.ZERO;

    @Column(name = "download_count_30d", nullable = false)
    private Long downloadCount30d = 0L;

    @Column(name = "lab_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal labScore = BigDecimal.ZERO;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillScoreSnapshot() {
    }

    public SkillScoreSnapshot(Long skillId) {
        this.skillId = skillId;
    }

    @PrePersist
    @PreUpdate
    protected void onWrite() {
        updatedAt = Instant.now(Clock.systemUTC());
    }

    public Long getSkillId() {
        return skillId;
    }

    public Long getLatestPublishedVersionId() {
        return latestPublishedVersionId;
    }

    public BigDecimal getTrustScore() {
        return trustScore;
    }

    public BigDecimal getQualityScore() {
        return qualityScore;
    }

    public BigDecimal getFeedbackScore() {
        return feedbackScore;
    }

    public BigDecimal getSuccessRate30d() {
        return successRate30d;
    }

    public BigDecimal getRatingBayes() {
        return ratingBayes;
    }

    public Long getDownloadCount30d() {
        return downloadCount30d;
    }

    public BigDecimal getLabScore() {
        return labScore;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setLatestPublishedVersionId(Long latestPublishedVersionId) {
        this.latestPublishedVersionId = latestPublishedVersionId;
    }

    public void setTrustScore(BigDecimal trustScore) {
        this.trustScore = trustScore;
    }

    public void setQualityScore(BigDecimal qualityScore) {
        this.qualityScore = qualityScore;
    }

    public void setFeedbackScore(BigDecimal feedbackScore) {
        this.feedbackScore = feedbackScore;
    }

    public void setSuccessRate30d(BigDecimal successRate30d) {
        this.successRate30d = successRate30d;
    }

    public void setRatingBayes(BigDecimal ratingBayes) {
        this.ratingBayes = ratingBayes;
    }

    public void setDownloadCount30d(Long downloadCount30d) {
        this.downloadCount30d = downloadCount30d;
    }

    public void setLabScore(BigDecimal labScore) {
        this.labScore = labScore;
    }
}

