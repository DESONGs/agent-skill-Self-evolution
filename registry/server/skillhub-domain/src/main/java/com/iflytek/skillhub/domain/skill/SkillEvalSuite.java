package com.iflytek.skillhub.domain.skill;

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
@Table(name = "skill_eval_suite")
public class SkillEvalSuite {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_version_id", nullable = false)
    private Long skillVersionId;

    @Column(name = "suite_key", nullable = false, length = 64)
    private String suiteKey;

    @Column(name = "display_name", length = 128)
    private String displayName;

    @Column(name = "suite_type", nullable = false, length = 32)
    private String suiteType;

    @Column(name = "entry_path", length = 512)
    private String entryPath;

    @Column(name = "gate_level", nullable = false, length = 32)
    private String gateLevel;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "config_json", columnDefinition = "jsonb")
    private String configJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "success_criteria_json", columnDefinition = "jsonb")
    private String successCriteriaJson;

    @Column(name = "latest_report_key", length = 512)
    private String latestReportKey;

    @Column(name = "created_by", length = 128)
    private String createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillEvalSuite() {
    }

    public SkillEvalSuite(Long skillVersionId,
                          String suiteKey,
                          String suiteType,
                          String gateLevel,
                          String createdBy) {
        this.skillVersionId = skillVersionId;
        this.suiteKey = suiteKey;
        this.suiteType = suiteType;
        this.gateLevel = gateLevel;
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

    public Long getSkillVersionId() {
        return skillVersionId;
    }

    public String getSuiteKey() {
        return suiteKey;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getSuiteType() {
        return suiteType;
    }

    public String getEntryPath() {
        return entryPath;
    }

    public String getGateLevel() {
        return gateLevel;
    }

    public String getConfigJson() {
        return configJson;
    }

    public String getSuccessCriteriaJson() {
        return successCriteriaJson;
    }

    public String getLatestReportKey() {
        return latestReportKey;
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

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public void setSuiteType(String suiteType) {
        this.suiteType = suiteType;
    }

    public void setEntryPath(String entryPath) {
        this.entryPath = entryPath;
    }

    public void setGateLevel(String gateLevel) {
        this.gateLevel = gateLevel;
    }

    public void setConfigJson(String configJson) {
        this.configJson = configJson;
    }

    public void setSuccessCriteriaJson(String successCriteriaJson) {
        this.successCriteriaJson = successCriteriaJson;
    }

    public void setLatestReportKey(String latestReportKey) {
        this.latestReportKey = latestReportKey;
    }
}
