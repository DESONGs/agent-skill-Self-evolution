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
@Table(name = "skill_action")
public class SkillAction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_version_id", nullable = false)
    private Long skillVersionId;

    @Column(name = "action_id", nullable = false, length = 64)
    private String actionId;

    @Column(name = "display_name", length = 128)
    private String displayName;

    @Column(name = "action_kind", nullable = false, length = 32)
    private String actionKind;

    @Column(name = "entry_path", nullable = false, length = 512)
    private String entryPath;

    @Column(name = "runtime_family", length = 64)
    private String runtimeFamily;

    @Column(name = "environment_profile_id")
    private Long environmentProfileId;

    @Column(name = "timeout_sec")
    private Integer timeoutSec;

    @Column(name = "sandbox_mode", length = 32)
    private String sandboxMode;

    @Column(name = "allow_network", nullable = false)
    private boolean allowNetwork = false;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "input_schema_json", columnDefinition = "jsonb")
    private String inputSchemaJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "output_schema_json", columnDefinition = "jsonb")
    private String outputSchemaJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "side_effects_json", columnDefinition = "jsonb")
    private String sideEffectsJson;

    @Column(name = "idempotency_mode", length = 32)
    private String idempotencyMode;

    @Column(name = "is_default_action", nullable = false)
    private boolean defaultAction = false;

    @Column(name = "created_by", length = 128)
    private String createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillAction() {
    }

    public SkillAction(Long skillVersionId,
                       String actionId,
                       String actionKind,
                       String entryPath,
                       String createdBy) {
        this.skillVersionId = skillVersionId;
        this.actionId = actionId;
        this.actionKind = actionKind;
        this.entryPath = entryPath;
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

    public String getActionId() {
        return actionId;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getActionKind() {
        return actionKind;
    }

    public String getEntryPath() {
        return entryPath;
    }

    public String getRuntimeFamily() {
        return runtimeFamily;
    }

    public Long getEnvironmentProfileId() {
        return environmentProfileId;
    }

    public Integer getTimeoutSec() {
        return timeoutSec;
    }

    public String getSandboxMode() {
        return sandboxMode;
    }

    public boolean isAllowNetwork() {
        return allowNetwork;
    }

    public String getInputSchemaJson() {
        return inputSchemaJson;
    }

    public String getOutputSchemaJson() {
        return outputSchemaJson;
    }

    public String getSideEffectsJson() {
        return sideEffectsJson;
    }

    public String getIdempotencyMode() {
        return idempotencyMode;
    }

    public boolean isDefaultAction() {
        return defaultAction;
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

    public void setActionKind(String actionKind) {
        this.actionKind = actionKind;
    }

    public void setEntryPath(String entryPath) {
        this.entryPath = entryPath;
    }

    public void setRuntimeFamily(String runtimeFamily) {
        this.runtimeFamily = runtimeFamily;
    }

    public void setEnvironmentProfileId(Long environmentProfileId) {
        this.environmentProfileId = environmentProfileId;
    }

    public void setTimeoutSec(Integer timeoutSec) {
        this.timeoutSec = timeoutSec;
    }

    public void setSandboxMode(String sandboxMode) {
        this.sandboxMode = sandboxMode;
    }

    public void setAllowNetwork(boolean allowNetwork) {
        this.allowNetwork = allowNetwork;
    }

    public void setInputSchemaJson(String inputSchemaJson) {
        this.inputSchemaJson = inputSchemaJson;
    }

    public void setOutputSchemaJson(String outputSchemaJson) {
        this.outputSchemaJson = outputSchemaJson;
    }

    public void setSideEffectsJson(String sideEffectsJson) {
        this.sideEffectsJson = sideEffectsJson;
    }

    public void setIdempotencyMode(String idempotencyMode) {
        this.idempotencyMode = idempotencyMode;
    }

    public void setDefaultAction(boolean defaultAction) {
        this.defaultAction = defaultAction;
    }
}
