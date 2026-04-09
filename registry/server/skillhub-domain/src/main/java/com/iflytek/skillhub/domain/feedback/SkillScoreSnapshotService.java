package com.iflytek.skillhub.domain.feedback;

import com.iflytek.skillhub.domain.security.SecurityAudit;
import com.iflytek.skillhub.domain.security.SecurityAuditRepository;
import com.iflytek.skillhub.domain.security.SecurityVerdict;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.domain.skill.SkillVersionStats;
import com.iflytek.skillhub.domain.skill.SkillVersionStatsRepository;
import com.iflytek.skillhub.domain.skill.service.SkillLifecycleProjectionService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service("feedbackSkillScoreSnapshotService")
public class SkillScoreSnapshotService {

    private static final BigDecimal ZERO = new BigDecimal("0.0000");
    private static final BigDecimal NEUTRAL = new BigDecimal("0.5000");
    private static final BigDecimal ONE = new BigDecimal("1.0000");
    private static final int SCALE = 4;
    private static final int MIN_GOVERNANCE_SAMPLE_SIZE = 10;

    public record SnapshotRefreshResult(int refreshedCount, List<Long> skillIds) {}

    private record RefreshResult(Long skillId, SkillScoreSnapshot snapshot, boolean changed) {}

    private final SkillRunFeedbackRepository skillRunFeedbackRepository;
    private final SkillScoreSnapshotRepository skillScoreSnapshotRepository;
    private final SkillRepository skillRepository;
    private final SkillVersionStatsRepository skillVersionStatsRepository;
    private final SkillLifecycleProjectionService skillLifecycleProjectionService;
    private final SecurityAuditRepository securityAuditRepository;
    private final Clock clock;

    public SkillScoreSnapshotService(SkillRunFeedbackRepository skillRunFeedbackRepository,
                                     SkillScoreSnapshotRepository skillScoreSnapshotRepository,
                                     SkillRepository skillRepository,
                                     SkillVersionStatsRepository skillVersionStatsRepository,
                                     SkillLifecycleProjectionService skillLifecycleProjectionService,
                                     SecurityAuditRepository securityAuditRepository,
                                     Clock clock) {
        this.skillRunFeedbackRepository = skillRunFeedbackRepository;
        this.skillScoreSnapshotRepository = skillScoreSnapshotRepository;
        this.skillRepository = skillRepository;
        this.skillVersionStatsRepository = skillVersionStatsRepository;
        this.skillLifecycleProjectionService = skillLifecycleProjectionService;
        this.securityAuditRepository = securityAuditRepository;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public List<SkillScoreSnapshot> listSnapshots() {
        return skillScoreSnapshotRepository.findAllByOrderByUpdatedAtDesc();
    }

    @Transactional(readOnly = true)
    public Optional<SkillScoreSnapshot> getSnapshot(Long skillId) {
        return skillScoreSnapshotRepository.findBySkillId(skillId);
    }

    @Transactional
    public SkillScoreSnapshot refreshSkillSnapshot(Long skillId) {
        Skill skill = skillRepository.findById(skillId)
                .orElseThrow(() -> new IllegalArgumentException("Skill not found: " + skillId));
        SkillLifecycleProjectionService.Projection projection =
                skillLifecycleProjectionService.projectPublishedSummaries(List.of(skill)).get(skillId);
        List<SkillRunFeedback> recentFeedback = skillRunFeedbackRepository.findBySkillIdAndObservedAtGreaterThanEqual(
                skillId,
                windowStart()
        );
        return refreshSnapshot(skill, projection, recentFeedback).snapshot();
    }

    @Transactional
    public SnapshotRefreshResult refreshAllSnapshots() {
        List<Skill> skills = skillRepository.findAll();
        if (skills.isEmpty()) {
            return new SnapshotRefreshResult(0, List.of());
        }

        Instant since = windowStart();
        Map<Long, SkillLifecycleProjectionService.Projection> projections =
                skillLifecycleProjectionService.projectPublishedSummaries(skills);
        Map<Long, List<SkillRunFeedback>> feedbackBySkillId = skillRunFeedbackRepository
                .findBySkillIdInAndObservedAtGreaterThanEqual(
                        skills.stream().map(Skill::getId).toList(),
                        since
                )
                .stream()
                .filter(feedback -> feedback.getSkillId() != null)
                .collect(Collectors.groupingBy(SkillRunFeedback::getSkillId));

        List<Long> changedSkillIds = new ArrayList<>();
        for (Skill skill : skills) {
            RefreshResult result = refreshSnapshot(
                    skill,
                    projections.get(skill.getId()),
                    feedbackBySkillId.getOrDefault(skill.getId(), List.of())
            );
            if (result.changed()) {
                changedSkillIds.add(skill.getId());
            }
        }
        return new SnapshotRefreshResult(changedSkillIds.size(), changedSkillIds);
    }

    @Transactional
    public int bootstrapMissingSnapshots() {
        return bootstrapMissingSnapshotsDetailed().refreshedCount();
    }

    @Transactional
    public SnapshotRefreshResult bootstrapMissingSnapshotsDetailed() {
        List<Skill> skills = skillRepository.findAll();
        if (skills.isEmpty()) {
            return new SnapshotRefreshResult(0, List.of());
        }

        Map<Long, SkillLifecycleProjectionService.Projection> projections =
                skillLifecycleProjectionService.projectPublishedSummaries(skills);
        List<Long> createdSkillIds = new ArrayList<>();
        for (Skill skill : skills) {
            if (skillScoreSnapshotRepository.findBySkillId(skill.getId()).isPresent()) {
                continue;
            }

            SkillScoreSnapshot snapshot = new SkillScoreSnapshot(skill.getId());
            Long latestPublishedVersionId = resolvePublishedVersionId(projections.get(skill.getId()));
            snapshot.setLatestPublishedVersionId(latestPublishedVersionId);

            long baselineDownloads = skill.getDownloadCount() == null ? 0L : skill.getDownloadCount();
            if (latestPublishedVersionId != null) {
                baselineDownloads = Math.max(
                        baselineDownloads,
                        skillVersionStatsRepository.findBySkillVersionId(latestPublishedVersionId)
                                .map(SkillVersionStats::getDownloadCount)
                                .orElse(0L)
                );
            }

            snapshot.setDownloadCount30d(baselineDownloads);
            snapshot.setFeedbackScore(NEUTRAL);
            snapshot.setRatingBayes(NEUTRAL);
            snapshot.setLabScore(NEUTRAL);
            snapshot.setSuccessRate30d(NEUTRAL);
            snapshot.setQualityScore(weighted(NEUTRAL, new BigDecimal("0.6"), NEUTRAL, new BigDecimal("0.4")));
            snapshot.setTrustScore(weighted(
                    NEUTRAL, new BigDecimal("0.5"),
                    resolveScanSafe(latestPublishedVersionId), new BigDecimal("0.3"),
                    NEUTRAL, new BigDecimal("0.2")
            ));
            skillScoreSnapshotRepository.save(snapshot);
            createdSkillIds.add(skill.getId());
        }
        return new SnapshotRefreshResult(createdSkillIds.size(), createdSkillIds);
    }

    private RefreshResult refreshSnapshot(Skill skill,
                                          SkillLifecycleProjectionService.Projection projection,
                                          List<SkillRunFeedback> recentFeedback) {
        SkillScoreSnapshot snapshot = skillScoreSnapshotRepository.findBySkillId(skill.getId())
                .orElseGet(() -> new SkillScoreSnapshot(skill.getId()));
        SkillScoreSnapshot before = copy(snapshot);

        Long latestPublishedVersionId = resolvePublishedVersionId(projection);
        BigDecimal feedbackScore = computeFeedbackScore(recentFeedback);
        BigDecimal ratingBayes = computeRatingBayes(recentFeedback);
        BigDecimal labScore = computeLabScore(recentFeedback);
        BigDecimal successRate = computeSuccessRate(recentFeedback);
        BigDecimal qualityScore = weighted(labScore, new BigDecimal("0.6"), feedbackScore, new BigDecimal("0.4"));
        BigDecimal trustScore = weighted(
                successRate, new BigDecimal("0.5"),
                resolveScanSafe(latestPublishedVersionId), new BigDecimal("0.3"),
                feedbackScore, new BigDecimal("0.2")
        );

        snapshot.setLatestPublishedVersionId(latestPublishedVersionId);
        snapshot.setDownloadCount30d(countDownloads(recentFeedback));
        snapshot.setFeedbackScore(feedbackScore);
        snapshot.setRatingBayes(ratingBayes);
        snapshot.setLabScore(labScore);
        snapshot.setSuccessRate30d(successRate);
        snapshot.setQualityScore(qualityScore);
        snapshot.setTrustScore(trustScore);

        SkillScoreSnapshot saved = skillScoreSnapshotRepository.save(snapshot);
        return new RefreshResult(skill.getId(), saved, !equivalent(before, saved));
    }

    private Long resolvePublishedVersionId(SkillLifecycleProjectionService.Projection projection) {
        return projection != null && projection.publishedVersion() != null
                ? projection.publishedVersion().id()
                : null;
    }

    private long countDownloads(List<SkillRunFeedback> feedback) {
        return feedback.stream()
                .filter(item -> "DOWNLOAD".equalsIgnoreCase(item.getFeedbackType()))
                .count();
    }

    private BigDecimal computeSuccessRate(List<SkillRunFeedback> feedback) {
        List<SkillRunFeedback> successSignals = feedback.stream()
                .filter(this::isSuccessSignal)
                .filter(item -> item.getSuccess() != null)
                .toList();
        if (successSignals.size() < MIN_GOVERNANCE_SAMPLE_SIZE) {
            return NEUTRAL;
        }
        long successes = successSignals.stream()
                .filter(SkillRunFeedback::getSuccess)
                .count();
        return ratio(successes, successSignals.size());
    }

    private BigDecimal computeFeedbackScore(List<SkillRunFeedback> feedback) {
        List<Integer> ratings = feedback.stream()
                .map(SkillRunFeedback::getRating)
                .filter(value -> value != null && value >= 1 && value <= 5)
                .toList();
        if (ratings.isEmpty()) {
            return NEUTRAL;
        }
        BigDecimal priorWeight = new BigDecimal("3.0");
        BigDecimal priorMean = NEUTRAL;
        BigDecimal sum = ratings.stream()
                .map(this::normalizeRating)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal numerator = sum.add(priorWeight.multiply(priorMean));
        BigDecimal denominator = priorWeight.add(BigDecimal.valueOf(ratings.size()));
        return scale(numerator.divide(denominator, SCALE, RoundingMode.HALF_UP));
    }

    private BigDecimal computeRatingBayes(List<SkillRunFeedback> feedback) {
        return computeFeedbackScore(feedback);
    }

    private BigDecimal computeLabScore(List<SkillRunFeedback> feedback) {
        List<SkillRunFeedback> labSignals = feedback.stream()
                .filter(item -> "LAB".equalsIgnoreCase(item.getFeedbackSource()))
                .toList();
        if (labSignals.isEmpty()) {
            return NEUTRAL;
        }

        List<SkillRunFeedback> explicitRatings = labSignals.stream()
                .filter(item -> item.getRating() != null && item.getRating() >= 1 && item.getRating() <= 5)
                .toList();
        if (!explicitRatings.isEmpty()) {
            BigDecimal total = explicitRatings.stream()
                    .map(item -> normalizeRating(item.getRating()))
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            return scale(total.divide(BigDecimal.valueOf(explicitRatings.size()), SCALE, RoundingMode.HALF_UP));
        }

        List<SkillRunFeedback> explicitSuccess = labSignals.stream()
                .filter(item -> item.getSuccess() != null)
                .toList();
        if (explicitSuccess.isEmpty()) {
            return NEUTRAL;
        }
        long successCount = explicitSuccess.stream()
                .filter(SkillRunFeedback::getSuccess)
                .count();
        return ratio(successCount, explicitSuccess.size());
    }

    private BigDecimal resolveScanSafe(Long latestPublishedVersionId) {
        if (latestPublishedVersionId == null) {
            return NEUTRAL;
        }
        Optional<SecurityAudit> latestAudit = securityAuditRepository.findLatestActiveByVersionId(latestPublishedVersionId)
                .stream()
                .max((left, right) -> resolveAuditOrderingTime(left).compareTo(resolveAuditOrderingTime(right)));
        if (latestAudit.isEmpty()) {
            return NEUTRAL;
        }
        return latestAudit.get().getVerdict() == SecurityVerdict.SAFE ? ONE : ZERO;
    }

    private Instant resolveAuditOrderingTime(SecurityAudit audit) {
        if (audit.getCreatedAt() != null) {
            return audit.getCreatedAt();
        }
        if (audit.getScannedAt() != null) {
            return audit.getScannedAt();
        }
        return Instant.EPOCH;
    }

    private boolean isSuccessSignal(SkillRunFeedback feedback) {
        if (feedback == null) {
            return false;
        }
        if ("LAB".equalsIgnoreCase(feedback.getFeedbackSource())) {
            return true;
        }
        String type = feedback.getFeedbackType();
        return "INSTALL".equalsIgnoreCase(type)
                || "EXECUTION".equalsIgnoreCase(type)
                || "EVAL_RESULT".equalsIgnoreCase(type);
    }

    private BigDecimal normalizeRating(Integer rating) {
        if (rating == null) {
            return NEUTRAL;
        }
        return scale(BigDecimal.valueOf(rating - 1L)
                .divide(new BigDecimal("4.0"), SCALE, RoundingMode.HALF_UP));
    }

    private BigDecimal ratio(long numerator, long denominator) {
        if (denominator <= 0) {
            return NEUTRAL;
        }
        return scale(BigDecimal.valueOf(numerator)
                .divide(BigDecimal.valueOf(denominator), SCALE, RoundingMode.HALF_UP));
    }

    private BigDecimal weighted(BigDecimal firstValue,
                                BigDecimal firstWeight,
                                BigDecimal secondValue,
                                BigDecimal secondWeight) {
        return scale(firstValue.multiply(firstWeight).add(secondValue.multiply(secondWeight)));
    }

    private BigDecimal weighted(BigDecimal firstValue,
                                BigDecimal firstWeight,
                                BigDecimal secondValue,
                                BigDecimal secondWeight,
                                BigDecimal thirdValue,
                                BigDecimal thirdWeight) {
        return scale(firstValue.multiply(firstWeight)
                .add(secondValue.multiply(secondWeight))
                .add(thirdValue.multiply(thirdWeight)));
    }

    private BigDecimal scale(BigDecimal value) {
        if (value == null) {
            return NEUTRAL;
        }
        return value.setScale(SCALE, RoundingMode.HALF_UP);
    }

    private SkillScoreSnapshot copy(SkillScoreSnapshot source) {
        SkillScoreSnapshot snapshot = new SkillScoreSnapshot(source.getSkillId());
        snapshot.setLatestPublishedVersionId(source.getLatestPublishedVersionId());
        snapshot.setTrustScore(source.getTrustScore());
        snapshot.setQualityScore(source.getQualityScore());
        snapshot.setFeedbackScore(source.getFeedbackScore());
        snapshot.setSuccessRate30d(source.getSuccessRate30d());
        snapshot.setRatingBayes(source.getRatingBayes());
        snapshot.setDownloadCount30d(source.getDownloadCount30d());
        snapshot.setLabScore(source.getLabScore());
        return snapshot;
    }

    private boolean equivalent(SkillScoreSnapshot left, SkillScoreSnapshot right) {
        if (left == null && right == null) {
            return true;
        }
        if (left == null || right == null) {
            return false;
        }
        return Objects.equals(left.getLatestPublishedVersionId(), right.getLatestPublishedVersionId())
                && Objects.equals(left.getTrustScore(), right.getTrustScore())
                && Objects.equals(left.getQualityScore(), right.getQualityScore())
                && Objects.equals(left.getFeedbackScore(), right.getFeedbackScore())
                && Objects.equals(left.getSuccessRate30d(), right.getSuccessRate30d())
                && Objects.equals(left.getRatingBayes(), right.getRatingBayes())
                && Objects.equals(left.getDownloadCount30d(), right.getDownloadCount30d())
                && Objects.equals(left.getLabScore(), right.getLabScore());
    }

    private Instant windowStart() {
        return Instant.now(clock).minus(30, ChronoUnit.DAYS);
    }
}
