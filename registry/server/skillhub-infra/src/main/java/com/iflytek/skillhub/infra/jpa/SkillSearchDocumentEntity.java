package com.iflytek.skillhub.infra.jpa;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "skill_search_document")
public class SkillSearchDocumentEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_id", nullable = false, unique = true)
    private Long skillId;

    @Column(name = "namespace_id", nullable = false)
    private Long namespaceId;

    @Column(name = "namespace_slug", nullable = false, length = 64)
    private String namespaceSlug;

    @Column(name = "owner_id", nullable = false, length = 128)
    private String ownerId;

    @Column(length = 512)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(columnDefinition = "TEXT")
    private String keywords;

    @Column(name = "search_text", columnDefinition = "TEXT")
    private String searchText;

    @Column(name = "semantic_vector", columnDefinition = "TEXT")
    private String semanticVector;

    @Column(nullable = false, length = 32)
    private String visibility;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(name = "latest_published_version_id")
    private Long latestPublishedVersionId;

    @Column(name = "latest_published_version", length = 64)
    private String latestPublishedVersion;

    @Column(name = "published_at")
    private Instant publishedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "label_slugs", columnDefinition = "jsonb", nullable = false)
    private String labelSlugs = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "runtime_tags", columnDefinition = "jsonb", nullable = false)
    private String runtimeTags = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "tool_tags", columnDefinition = "jsonb", nullable = false)
    private String toolTags = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "action_kinds", columnDefinition = "jsonb", nullable = false)
    private String actionKinds = "[]";

    @Column(name = "trust_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal trustScore = new BigDecimal("0.5000");

    @Column(name = "quality_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal qualityScore = new BigDecimal("0.5000");

    @Column(name = "feedback_score", precision = 10, scale = 4, nullable = false)
    private BigDecimal feedbackScore = new BigDecimal("0.5000");

    @Column(name = "success_rate_30d", precision = 10, scale = 4, nullable = false)
    private BigDecimal successRate30d = new BigDecimal("0.5000");

    @Column(name = "scan_verdict", length = 32)
    private String scanVerdict;

    @Column(name = "review_state", length = 32)
    private String reviewState;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    protected SkillSearchDocumentEntity() {
    }

    public SkillSearchDocumentEntity(
            Long skillId,
            Long namespaceId,
            String namespaceSlug,
            String ownerId,
            String title,
            String summary,
            String keywords,
            String searchText,
            String semanticVector,
            String visibility,
            String status) {
        this(
                skillId,
                namespaceId,
                namespaceSlug,
                ownerId,
                title,
                summary,
                keywords,
                searchText,
                semanticVector,
                visibility,
                status,
                null,
                null,
                null,
                "[]",
                "[]",
                "[]",
                "[]",
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                new BigDecimal("0.5000"),
                "UNKNOWN",
                "UNKNOWN"
        );
    }

    public SkillSearchDocumentEntity(
            Long skillId,
            Long namespaceId,
            String namespaceSlug,
            String ownerId,
            String title,
            String summary,
            String keywords,
            String searchText,
            String semanticVector,
            String visibility,
            String status,
            Long latestPublishedVersionId,
            String latestPublishedVersion,
            Instant publishedAt,
            String labelSlugs,
            String runtimeTags,
            String toolTags,
            String actionKinds,
            BigDecimal trustScore,
            BigDecimal qualityScore,
            BigDecimal feedbackScore,
            BigDecimal successRate30d,
            String scanVerdict,
            String reviewState) {
        this.skillId = skillId;
        this.namespaceId = namespaceId;
        this.namespaceSlug = namespaceSlug;
        this.ownerId = ownerId;
        this.title = title;
        this.summary = summary;
        this.keywords = keywords;
        this.searchText = searchText;
        this.semanticVector = semanticVector;
        this.visibility = visibility;
        this.status = status;
        this.latestPublishedVersionId = latestPublishedVersionId;
        this.latestPublishedVersion = latestPublishedVersion;
        this.publishedAt = publishedAt;
        this.labelSlugs = labelSlugs;
        this.runtimeTags = runtimeTags;
        this.toolTags = toolTags;
        this.actionKinds = actionKinds;
        this.trustScore = trustScore;
        this.qualityScore = qualityScore;
        this.feedbackScore = feedbackScore;
        this.successRate30d = successRate30d;
        this.scanVerdict = scanVerdict;
        this.reviewState = reviewState;
    }

    @PrePersist
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    // Getters
    public Long getId() {
        return id;
    }

    public Long getSkillId() {
        return skillId;
    }

    public Long getNamespaceId() {
        return namespaceId;
    }

    public String getNamespaceSlug() {
        return namespaceSlug;
    }

    public String getOwnerId() {
        return ownerId;
    }

    public String getTitle() {
        return title;
    }

    public String getSummary() {
        return summary;
    }

    public String getKeywords() {
        return keywords;
    }

    public String getSearchText() {
        return searchText;
    }

    public String getVisibility() {
        return visibility;
    }

    public String getSemanticVector() {
        return semanticVector;
    }

    public String getStatus() {
        return status;
    }

    public Long getLatestPublishedVersionId() {
        return latestPublishedVersionId;
    }

    public String getLatestPublishedVersion() {
        return latestPublishedVersion;
    }

    public Instant getPublishedAt() {
        return publishedAt;
    }

    public String getLabelSlugs() {
        return labelSlugs;
    }

    public String getRuntimeTags() {
        return runtimeTags;
    }

    public String getToolTags() {
        return toolTags;
    }

    public String getActionKinds() {
        return actionKinds;
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

    public String getScanVerdict() {
        return scanVerdict;
    }

    public String getReviewState() {
        return reviewState;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    // Setters
    public void setNamespaceId(Long namespaceId) {
        this.namespaceId = namespaceId;
    }

    public void setNamespaceSlug(String namespaceSlug) {
        this.namespaceSlug = namespaceSlug;
    }

    public void setOwnerId(String ownerId) {
        this.ownerId = ownerId;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public void setKeywords(String keywords) {
        this.keywords = keywords;
    }

    public void setSearchText(String searchText) {
        this.searchText = searchText;
    }

    public void setSemanticVector(String semanticVector) {
        this.semanticVector = semanticVector;
    }

    public void setVisibility(String visibility) {
        this.visibility = visibility;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public void setLatestPublishedVersionId(Long latestPublishedVersionId) {
        this.latestPublishedVersionId = latestPublishedVersionId;
    }

    public void setLatestPublishedVersion(String latestPublishedVersion) {
        this.latestPublishedVersion = latestPublishedVersion;
    }

    public void setPublishedAt(Instant publishedAt) {
        this.publishedAt = publishedAt;
    }

    public void setLabelSlugs(String labelSlugs) {
        this.labelSlugs = labelSlugs;
    }

    public void setRuntimeTags(String runtimeTags) {
        this.runtimeTags = runtimeTags;
    }

    public void setToolTags(String toolTags) {
        this.toolTags = toolTags;
    }

    public void setActionKinds(String actionKinds) {
        this.actionKinds = actionKinds;
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

    public void setScanVerdict(String scanVerdict) {
        this.scanVerdict = scanVerdict;
    }

    public void setReviewState(String reviewState) {
        this.reviewState = reviewState;
    }
}
