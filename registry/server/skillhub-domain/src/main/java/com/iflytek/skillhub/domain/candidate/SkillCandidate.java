package com.iflytek.skillhub.domain.candidate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Clock;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "skill_candidate")
public class SkillCandidate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "candidate_key", nullable = false, length = 128, unique = true)
    private String candidateKey;

    @Column(name = "candidate_slug", nullable = false, length = 128)
    private String candidateSlug;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "candidate_spec_json", columnDefinition = "jsonb", nullable = false)
    private String candidateSpecJson = "{}";

    @Column(name = "source_kind", nullable = false, length = 32)
    private String sourceKind;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "source_refs_json", columnDefinition = "jsonb", nullable = false)
    private String sourceRefsJson = "[]";

    @Column(name = "problem_statement", columnDefinition = "TEXT")
    private String problemStatement;

    @Column(name = "target_user", length = 256)
    private String targetUser;

    @Column(name = "skill_boundary", columnDefinition = "TEXT")
    private String skillBoundary;

    @Column(name = "trigger_description", columnDefinition = "TEXT")
    private String triggerDescription;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "anti_triggers_json", columnDefinition = "jsonb", nullable = false)
    private String antiTriggersJson = "[]";

    @Column(name = "default_action_id", length = 128)
    private String defaultActionId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "governance_json", columnDefinition = "jsonb", nullable = false)
    private String governanceJson = "{}";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metrics_json", columnDefinition = "jsonb", nullable = false)
    private String metricsJson = "{}";

    @Column(name = "generated_bundle_key", length = 512)
    private String generatedBundleKey;

    @Column(name = "generated_manifest_key", length = 512)
    private String generatedManifestKey;

    @Column(name = "report_index_key", length = 512)
    private String reportIndexKey;

    @Column(name = "latest_lab_run_id", length = 128)
    private String latestLabRunId;

    @Column(name = "promotion_state", nullable = false, length = 32)
    private String promotionState;

    @Column(name = "source_skill_id")
    private Long sourceSkillId;

    @Column(name = "source_version_id")
    private Long sourceVersionId;

    @Column(name = "published_skill_id")
    private Long publishedSkillId;

    @Column(name = "published_version_id")
    private Long publishedVersionId;

    @Column(name = "created_by", length = 128)
    private String createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillCandidate() {
    }

    public SkillCandidate(String candidateKey,
                          String candidateSlug,
                          String sourceKind,
                          String candidateSpecJson,
                          String sourceRefsJson,
                          String problemStatement,
                          String targetUser,
                          String skillBoundary,
                          String triggerDescription,
                          String antiTriggersJson,
                          String defaultActionId,
                          String governanceJson,
                          String metricsJson,
                          String generatedBundleKey,
                          String generatedManifestKey,
                          String reportIndexKey,
                          String latestLabRunId,
                          String promotionState,
                          Long sourceSkillId,
                          Long sourceVersionId,
                          Long publishedSkillId,
                          Long publishedVersionId,
                          String createdBy) {
        this.candidateKey = candidateKey;
        this.candidateSlug = candidateSlug;
        this.sourceKind = sourceKind;
        this.candidateSpecJson = candidateSpecJson;
        this.sourceRefsJson = sourceRefsJson;
        this.problemStatement = problemStatement;
        this.targetUser = targetUser;
        this.skillBoundary = skillBoundary;
        this.triggerDescription = triggerDescription;
        this.antiTriggersJson = antiTriggersJson;
        this.defaultActionId = defaultActionId;
        this.governanceJson = governanceJson;
        this.metricsJson = metricsJson;
        this.generatedBundleKey = generatedBundleKey;
        this.generatedManifestKey = generatedManifestKey;
        this.reportIndexKey = reportIndexKey;
        this.latestLabRunId = latestLabRunId;
        this.promotionState = promotionState;
        this.sourceSkillId = sourceSkillId;
        this.sourceVersionId = sourceVersionId;
        this.publishedSkillId = publishedSkillId;
        this.publishedVersionId = publishedVersionId;
        this.createdBy = createdBy;
    }

    @PrePersist
    protected void onCreate() {
        Instant now = Instant.now(Clock.systemUTC());
        createdAt = now;
        updatedAt = now;
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = Instant.now(Clock.systemUTC());
    }

    public Long getId() {
        return id;
    }

    public String getCandidateKey() {
        return candidateKey;
    }

    public String getCandidateSlug() {
        return candidateSlug;
    }

    public String getCandidateSpecJson() {
        return candidateSpecJson;
    }

    public String getSourceKind() {
        return sourceKind;
    }

    public String getSourceRefsJson() {
        return sourceRefsJson;
    }

    public String getProblemStatement() {
        return problemStatement;
    }

    public String getTargetUser() {
        return targetUser;
    }

    public String getSkillBoundary() {
        return skillBoundary;
    }

    public String getTriggerDescription() {
        return triggerDescription;
    }

    public String getAntiTriggersJson() {
        return antiTriggersJson;
    }

    public String getDefaultActionId() {
        return defaultActionId;
    }

    public String getGovernanceJson() {
        return governanceJson;
    }

    public String getMetricsJson() {
        return metricsJson;
    }

    public String getGeneratedBundleKey() {
        return generatedBundleKey;
    }

    public String getGeneratedManifestKey() {
        return generatedManifestKey;
    }

    public String getReportIndexKey() {
        return reportIndexKey;
    }

    public String getLatestLabRunId() {
        return latestLabRunId;
    }

    public String getPromotionState() {
        return promotionState;
    }

    public Long getSourceSkillId() {
        return sourceSkillId;
    }

    public Long getSourceVersionId() {
        return sourceVersionId;
    }

    public Long getPublishedSkillId() {
        return publishedSkillId;
    }

    public Long getPublishedVersionId() {
        return publishedVersionId;
    }

    public String getCreatedBy() {
        return createdBy;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setCandidateSlug(String candidateSlug) {
        this.candidateSlug = candidateSlug;
    }

    public void setCandidateSpecJson(String candidateSpecJson) {
        this.candidateSpecJson = candidateSpecJson;
    }

    public void setSourceKind(String sourceKind) {
        this.sourceKind = sourceKind;
    }

    public void setSourceRefsJson(String sourceRefsJson) {
        this.sourceRefsJson = sourceRefsJson;
    }

    public void setProblemStatement(String problemStatement) {
        this.problemStatement = problemStatement;
    }

    public void setTargetUser(String targetUser) {
        this.targetUser = targetUser;
    }

    public void setSkillBoundary(String skillBoundary) {
        this.skillBoundary = skillBoundary;
    }

    public void setTriggerDescription(String triggerDescription) {
        this.triggerDescription = triggerDescription;
    }

    public void setAntiTriggersJson(String antiTriggersJson) {
        this.antiTriggersJson = antiTriggersJson;
    }

    public void setDefaultActionId(String defaultActionId) {
        this.defaultActionId = defaultActionId;
    }

    public void setGovernanceJson(String governanceJson) {
        this.governanceJson = governanceJson;
    }

    public void setMetricsJson(String metricsJson) {
        this.metricsJson = metricsJson;
    }

    public void setGeneratedBundleKey(String generatedBundleKey) {
        this.generatedBundleKey = generatedBundleKey;
    }

    public void setGeneratedManifestKey(String generatedManifestKey) {
        this.generatedManifestKey = generatedManifestKey;
    }

    public void setReportIndexKey(String reportIndexKey) {
        this.reportIndexKey = reportIndexKey;
    }

    public void setLatestLabRunId(String latestLabRunId) {
        this.latestLabRunId = latestLabRunId;
    }

    public void setPromotionState(String promotionState) {
        this.promotionState = promotionState;
    }

    public void setSourceSkillId(Long sourceSkillId) {
        this.sourceSkillId = sourceSkillId;
    }

    public void setSourceVersionId(Long sourceVersionId) {
        this.sourceVersionId = sourceVersionId;
    }

    public void setPublishedSkillId(Long publishedSkillId) {
        this.publishedSkillId = publishedSkillId;
    }

    public void setPublishedVersionId(Long publishedVersionId) {
        this.publishedVersionId = publishedVersionId;
    }

    public void setCreatedBy(String createdBy) {
        this.createdBy = createdBy;
    }
}
