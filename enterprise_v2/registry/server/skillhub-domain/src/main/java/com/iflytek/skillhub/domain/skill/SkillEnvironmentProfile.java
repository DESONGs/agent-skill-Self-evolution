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
@Table(name = "skill_environment_profile")
public class SkillEnvironmentProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_version_id", nullable = false)
    private Long skillVersionId;

    @Column(name = "profile_key", nullable = false, length = 64)
    private String profileKey;

    @Column(name = "display_name", length = 128)
    private String displayName;

    @Column(name = "runtime_family", length = 64)
    private String runtimeFamily;

    @Column(name = "runtime_version_range", length = 64)
    private String runtimeVersionRange;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "tool_requirements_json", columnDefinition = "jsonb")
    private String toolRequirementsJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "capability_tags_json", columnDefinition = "jsonb")
    private String capabilityTagsJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "os_constraints_json", columnDefinition = "jsonb")
    private String osConstraintsJson;

    @Column(name = "network_policy", length = 32)
    private String networkPolicy;

    @Column(name = "filesystem_policy", length = 32)
    private String filesystemPolicy;

    @Column(name = "sandbox_mode", length = 32)
    private String sandboxMode;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "resource_limits_json", columnDefinition = "jsonb")
    private String resourceLimitsJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "env_schema_json", columnDefinition = "jsonb")
    private String envSchemaJson;

    @Column(name = "is_default_profile", nullable = false)
    private boolean defaultProfile = false;

    @Column(name = "created_by", length = 128)
    private String createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillEnvironmentProfile() {
    }

    public SkillEnvironmentProfile(Long skillVersionId, String profileKey, String createdBy) {
        this.skillVersionId = skillVersionId;
        this.profileKey = profileKey;
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

    public String getProfileKey() {
        return profileKey;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getRuntimeFamily() {
        return runtimeFamily;
    }

    public String getRuntimeVersionRange() {
        return runtimeVersionRange;
    }

    public String getToolRequirementsJson() {
        return toolRequirementsJson;
    }

    public String getCapabilityTagsJson() {
        return capabilityTagsJson;
    }

    public String getOsConstraintsJson() {
        return osConstraintsJson;
    }

    public String getNetworkPolicy() {
        return networkPolicy;
    }

    public String getFilesystemPolicy() {
        return filesystemPolicy;
    }

    public String getSandboxMode() {
        return sandboxMode;
    }

    public String getResourceLimitsJson() {
        return resourceLimitsJson;
    }

    public String getEnvSchemaJson() {
        return envSchemaJson;
    }

    public boolean isDefaultProfile() {
        return defaultProfile;
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

    public void setRuntimeFamily(String runtimeFamily) {
        this.runtimeFamily = runtimeFamily;
    }

    public void setRuntimeVersionRange(String runtimeVersionRange) {
        this.runtimeVersionRange = runtimeVersionRange;
    }

    public void setToolRequirementsJson(String toolRequirementsJson) {
        this.toolRequirementsJson = toolRequirementsJson;
    }

    public void setCapabilityTagsJson(String capabilityTagsJson) {
        this.capabilityTagsJson = capabilityTagsJson;
    }

    public void setOsConstraintsJson(String osConstraintsJson) {
        this.osConstraintsJson = osConstraintsJson;
    }

    public void setNetworkPolicy(String networkPolicy) {
        this.networkPolicy = networkPolicy;
    }

    public void setFilesystemPolicy(String filesystemPolicy) {
        this.filesystemPolicy = filesystemPolicy;
    }

    public void setSandboxMode(String sandboxMode) {
        this.sandboxMode = sandboxMode;
    }

    public void setResourceLimitsJson(String resourceLimitsJson) {
        this.resourceLimitsJson = resourceLimitsJson;
    }

    public void setEnvSchemaJson(String envSchemaJson) {
        this.envSchemaJson = envSchemaJson;
    }

    public void setDefaultProfile(boolean defaultProfile) {
        this.defaultProfile = defaultProfile;
    }
}
