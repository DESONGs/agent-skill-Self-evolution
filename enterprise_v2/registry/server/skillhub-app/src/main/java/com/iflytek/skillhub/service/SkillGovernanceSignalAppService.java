package com.iflytek.skillhub.service;

import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshot;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotRepository;
import com.iflytek.skillhub.domain.namespace.Namespace;
import com.iflytek.skillhub.domain.namespace.NamespaceRepository;
import com.iflytek.skillhub.domain.skill.Skill;
import com.iflytek.skillhub.domain.skill.SkillRepository;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalItemResponse;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalResponse;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalSummaryResponse;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalsResponse;
import java.math.BigDecimal;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class SkillGovernanceSignalAppService {
    private static final BigDecimal LOW_SUCCESS_THRESHOLD = new BigDecimal("0.6000");
    private static final BigDecimal LOW_FEEDBACK_THRESHOLD = new BigDecimal("0.4500");
    private static final BigDecimal HIGH_RISK_TRUST_THRESHOLD = new BigDecimal("0.5500");
    private static final long HIGH_IMPACT_DOWNLOAD_THRESHOLD = 50L;

    private final SkillScoreSnapshotRepository skillScoreSnapshotRepository;
    private final SkillRepository skillRepository;
    private final NamespaceRepository namespaceRepository;
    private final SkillCandidateRepository skillCandidateRepository;

    public SkillGovernanceSignalAppService(SkillScoreSnapshotRepository skillScoreSnapshotRepository,
                                           SkillRepository skillRepository,
                                           NamespaceRepository namespaceRepository,
                                           SkillCandidateRepository skillCandidateRepository) {
        this.skillScoreSnapshotRepository = skillScoreSnapshotRepository;
        this.skillRepository = skillRepository;
        this.namespaceRepository = namespaceRepository;
        this.skillCandidateRepository = skillCandidateRepository;
    }

    public List<SkillGovernanceSignalResponse> listSkillSignals() {
        List<SkillScoreSnapshot> snapshots = skillScoreSnapshotRepository.findAllByOrderByUpdatedAtDesc();
        if (snapshots.isEmpty()) {
            return List.of();
        }

        List<Long> skillIds = snapshots.stream().map(SkillScoreSnapshot::getSkillId).toList();
        Map<Long, Skill> skillsById = skillRepository.findByIdIn(skillIds).stream()
                .collect(Collectors.toMap(Skill::getId, Function.identity()));
        List<Long> namespaceIds = skillsById.values().stream()
                .map(Skill::getNamespaceId)
                .distinct()
                .toList();
        Map<Long, Namespace> namespacesById = namespaceIds.isEmpty()
                ? Map.of()
                : namespaceRepository.findByIdIn(namespaceIds).stream()
                        .collect(Collectors.toMap(Namespace::getId, Function.identity()));

        return snapshots.stream()
                .flatMap(snapshot -> toSignals(snapshot, skillsById.get(snapshot.getSkillId()), namespacesById).stream())
                .sorted(Comparator
                        .comparing(SkillGovernanceSignalResponse::signalType)
                        .thenComparing(SkillGovernanceSignalResponse::trustScore, Comparator.nullsLast(BigDecimal::compareTo))
                        .thenComparing(SkillGovernanceSignalResponse::successRate30d, Comparator.nullsLast(BigDecimal::compareTo)))
                .toList();
    }

    public SkillGovernanceSignalsResponse listSkillSignals(Integer limit) {
        List<SkillGovernanceSignalResponse> signals = listSkillSignals();
        List<SkillGovernanceSignalResponse> limited = limit == null || limit <= 0 || signals.size() <= limit
                ? signals
                : signals.stream().limit(limit).toList();
        return new SkillGovernanceSignalsResponse(
                new SkillGovernanceSignalSummaryResponse(
                        distinctSkillCount(limited, signal -> "LOW_SUCCESS".equals(signal.signalType())),
                        distinctSkillCount(limited, signal -> signal.feedbackScore() != null
                                && signal.feedbackScore().compareTo(LOW_FEEDBACK_THRESHOLD) < 0),
                        distinctSkillCount(limited, signal -> "HIGH_RISK_HIGH_IMPACT".equals(signal.signalType())),
                        skillCandidateRepository.findByPromotionState("PROMOTION_PENDING").size(),
                        skillCandidateRepository.findByPromotionState("REJECTED").size()
                ),
                limited.stream().map(this::toItem).toList()
        );
    }

    private List<SkillGovernanceSignalResponse> toSignals(SkillScoreSnapshot snapshot,
                                                          Skill skill,
                                                          Map<Long, Namespace> namespacesById) {
        if (skill == null) {
            return List.of();
        }
        Namespace namespace = namespacesById.get(skill.getNamespaceId());
        String namespaceSlug = namespace != null ? namespace.getSlug() : null;

        SkillGovernanceSignalResponse lowSuccess = null;
        if (snapshot.getSuccessRate30d() != null
                && snapshot.getSuccessRate30d().compareTo(LOW_SUCCESS_THRESHOLD) < 0) {
            lowSuccess = new SkillGovernanceSignalResponse(
                    "LOW_SUCCESS",
                    skill.getId(),
                    namespaceSlug,
                    skill.getSlug(),
                    skill.getDisplayName(),
                    snapshot.getTrustScore(),
                    snapshot.getQualityScore(),
                    snapshot.getFeedbackScore(),
                    snapshot.getSuccessRate30d(),
                    snapshot.getDownloadCount30d(),
                    "QUEUE_REVIEW"
            );
        }

        SkillGovernanceSignalResponse highRiskImpact = null;
        if (snapshot.getTrustScore() != null
                && snapshot.getTrustScore().compareTo(HIGH_RISK_TRUST_THRESHOLD) < 0
                && snapshot.getDownloadCount30d() != null
                && snapshot.getDownloadCount30d() >= HIGH_IMPACT_DOWNLOAD_THRESHOLD) {
            highRiskImpact = new SkillGovernanceSignalResponse(
                    "HIGH_RISK_HIGH_IMPACT",
                    skill.getId(),
                    namespaceSlug,
                    skill.getSlug(),
                    skill.getDisplayName(),
                    snapshot.getTrustScore(),
                    snapshot.getQualityScore(),
                    snapshot.getFeedbackScore(),
                    snapshot.getSuccessRate30d(),
                    snapshot.getDownloadCount30d(),
                    "PRIORITIZE_GOVERNANCE"
            );
        }

        return java.util.stream.Stream.of(lowSuccess, highRiskImpact)
                .filter(java.util.Objects::nonNull)
                .toList();
    }

    private SkillGovernanceSignalItemResponse toItem(SkillGovernanceSignalResponse signal) {
        return new SkillGovernanceSignalItemResponse(
                signal.skillId(),
                signal.slug(),
                signal.displayName(),
                null,
                null,
                signal.trustScore(),
                signal.qualityScore(),
                signal.feedbackScore(),
                signal.successRate30d(),
                signal.downloadCount30d(),
                null,
                List.of(signal.signalType(), signal.recommendedAction()),
                List.of()
        );
    }

    private long distinctSkillCount(List<SkillGovernanceSignalResponse> signals,
                                    java.util.function.Predicate<SkillGovernanceSignalResponse> predicate) {
        return signals.stream()
                .filter(predicate)
                .map(SkillGovernanceSignalResponse::skillId)
                .distinct()
                .count();
    }
}
