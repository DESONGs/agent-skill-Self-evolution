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

@Entity
@Table(name = "skill_bundle_artifact")
public class SkillBundleArtifact {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_version_id", nullable = false, unique = true)
    private Long skillVersionId;

    @Column(name = "storage_key", nullable = false, length = 512)
    private String storageKey;

    @Column(name = "content_type", length = 128)
    private String contentType;

    @Column(length = 64)
    private String sha256;

    @Column(name = "size_bytes", nullable = false)
    private Long sizeBytes = 0L;

    @Column(name = "build_status", nullable = false, length = 32)
    private String buildStatus;

    @Column(name = "manifest_digest", length = 64)
    private String manifestDigest;

    @Column(name = "built_by", length = 128)
    private String builtBy;

    @Column(name = "built_at")
    private Instant builtAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SkillBundleArtifact() {
    }

    public SkillBundleArtifact(Long skillVersionId,
                               String storageKey,
                               String contentType,
                               String sha256,
                               Long sizeBytes,
                               String buildStatus,
                               String builtBy) {
        this.skillVersionId = skillVersionId;
        this.storageKey = storageKey;
        this.contentType = contentType;
        this.sha256 = sha256;
        this.sizeBytes = sizeBytes;
        this.buildStatus = buildStatus;
        this.builtBy = builtBy;
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

    public String getStorageKey() {
        return storageKey;
    }

    public String getContentType() {
        return contentType;
    }

    public String getSha256() {
        return sha256;
    }

    public Long getSizeBytes() {
        return sizeBytes;
    }

    public String getBuildStatus() {
        return buildStatus;
    }

    public String getManifestDigest() {
        return manifestDigest;
    }

    public String getBuiltBy() {
        return builtBy;
    }

    public Instant getBuiltAt() {
        return builtAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setStorageKey(String storageKey) {
        this.storageKey = storageKey;
    }

    public void setContentType(String contentType) {
        this.contentType = contentType;
    }

    public void setSha256(String sha256) {
        this.sha256 = sha256;
    }

    public void setSizeBytes(Long sizeBytes) {
        this.sizeBytes = sizeBytes;
    }

    public void setBuildStatus(String buildStatus) {
        this.buildStatus = buildStatus;
    }

    public void setManifestDigest(String manifestDigest) {
        this.manifestDigest = manifestDigest;
    }

    public void setBuiltBy(String builtBy) {
        this.builtBy = builtBy;
    }

    public void setBuiltAt(Instant builtAt) {
        this.builtAt = builtAt;
    }
}
