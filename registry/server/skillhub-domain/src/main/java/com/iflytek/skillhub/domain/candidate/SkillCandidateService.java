package com.iflytek.skillhub.domain.candidate;

import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import com.iflytek.skillhub.domain.shared.exception.DomainNotFoundException;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service("candidateIngressSkillCandidateService")
public class SkillCandidateService {

    public static final String STATE_CREATED = "CREATED";
    public static final String STATE_NORMALIZED = "NORMALIZED";
    public static final String STATE_LAB_READY = "LAB_READY";
    public static final String STATE_EVALUATED = "EVALUATED";
    public static final String STATE_GATE_PASSED = "GATE_PASSED";
    public static final String STATE_PROMOTION_PENDING = "PROMOTION_PENDING";
    public static final String STATE_PUBLISHED = "PUBLISHED";
    public static final String STATE_REJECTED = "REJECTED";
    public static final String STATE_SUPERSEDED = "SUPERSEDED";
    public static final String STATE_ARCHIVED = "ARCHIVED";

    public record UpsertCommand(
            String candidateKey,
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
            String actorId
    ) {}

    private static final Set<String> ALLOWED_STATES = Set.of(
            STATE_CREATED,
            STATE_NORMALIZED,
            STATE_LAB_READY,
            STATE_EVALUATED,
            STATE_GATE_PASSED,
            STATE_PROMOTION_PENDING,
            STATE_PUBLISHED,
            STATE_REJECTED,
            STATE_SUPERSEDED,
            STATE_ARCHIVED
    );

    private final SkillCandidateRepository skillCandidateRepository;

    public SkillCandidateService(SkillCandidateRepository skillCandidateRepository) {
        this.skillCandidateRepository = skillCandidateRepository;
    }

    @Transactional
    public SkillCandidate createCandidate(UpsertCommand command) {
        String candidateKey = requireText(command.candidateKey(), "candidate.key.required");
        skillCandidateRepository.findByCandidateKey(candidateKey)
                .ifPresent(existing -> {
                    throw new DomainBadRequestException("candidate.key.exists", candidateKey);
                });

        SkillCandidate candidate = new SkillCandidate(
                candidateKey,
                requireText(command.candidateSlug(), "candidate.slug.required"),
                requireText(command.sourceKind(), "candidate.source_kind.required"),
                normalizeObjectJson(command.candidateSpecJson()),
                normalizeArrayJson(command.sourceRefsJson()),
                command.problemStatement(),
                command.targetUser(),
                command.skillBoundary(),
                command.triggerDescription(),
                normalizeArrayJson(command.antiTriggersJson()),
                command.defaultActionId(),
                normalizeObjectJson(command.governanceJson()),
                normalizeObjectJson(command.metricsJson()),
                command.generatedBundleKey(),
                command.generatedManifestKey(),
                command.reportIndexKey(),
                command.latestLabRunId(),
                normalizeState(command.promotionState(), STATE_CREATED),
                command.sourceSkillId(),
                command.sourceVersionId(),
                null,
                null,
                command.actorId()
        );
        return skillCandidateRepository.save(candidate);
    }

    @Transactional(readOnly = true)
    public SkillCandidate getCandidate(Long candidateId) {
        return skillCandidateRepository.findById(candidateId)
                .orElseThrow(() -> new DomainNotFoundException("candidate.not_found", candidateId));
    }

    @Transactional(readOnly = true)
    public List<SkillCandidate> listCandidates(String promotionState) {
        if (promotionState == null || promotionState.isBlank()) {
            return skillCandidateRepository.findAllByOrderByUpdatedAtDesc();
        }
        return skillCandidateRepository.findByPromotionState(normalizeState(promotionState, STATE_CREATED))
                .stream()
                .sorted(Comparator.comparing(SkillCandidate::getUpdatedAt, Comparator.nullsLast(Comparator.reverseOrder())))
                .toList();
    }

    @Transactional
    public SkillCandidate updateCandidate(Long candidateId, UpsertCommand command) {
        SkillCandidate candidate = getCandidate(candidateId);
        if (command.candidateSlug() != null) {
            candidate.setCandidateSlug(requireText(command.candidateSlug(), "candidate.slug.required"));
        }
        if (command.sourceKind() != null) {
            candidate.setSourceKind(requireText(command.sourceKind(), "candidate.source_kind.required"));
        }
        if (command.candidateSpecJson() != null) {
            candidate.setCandidateSpecJson(normalizeObjectJson(command.candidateSpecJson()));
        }
        if (command.sourceRefsJson() != null) {
            candidate.setSourceRefsJson(normalizeArrayJson(command.sourceRefsJson()));
        }
        if (command.problemStatement() != null) {
            candidate.setProblemStatement(command.problemStatement());
        }
        if (command.targetUser() != null) {
            candidate.setTargetUser(command.targetUser());
        }
        if (command.skillBoundary() != null) {
            candidate.setSkillBoundary(command.skillBoundary());
        }
        if (command.triggerDescription() != null) {
            candidate.setTriggerDescription(command.triggerDescription());
        }
        if (command.antiTriggersJson() != null) {
            candidate.setAntiTriggersJson(normalizeArrayJson(command.antiTriggersJson()));
        }
        if (command.defaultActionId() != null) {
            candidate.setDefaultActionId(command.defaultActionId());
        }
        if (command.governanceJson() != null) {
            candidate.setGovernanceJson(normalizeObjectJson(command.governanceJson()));
        }
        if (command.metricsJson() != null) {
            candidate.setMetricsJson(normalizeObjectJson(command.metricsJson()));
        }
        if (command.generatedBundleKey() != null) {
            candidate.setGeneratedBundleKey(command.generatedBundleKey());
        }
        if (command.generatedManifestKey() != null) {
            candidate.setGeneratedManifestKey(command.generatedManifestKey());
        }
        if (command.reportIndexKey() != null) {
            candidate.setReportIndexKey(command.reportIndexKey());
        }
        if (command.latestLabRunId() != null) {
            candidate.setLatestLabRunId(command.latestLabRunId());
        }
        if (command.promotionState() != null) {
            candidate.setPromotionState(normalizeState(command.promotionState(), candidate.getPromotionState()));
        }
        if (command.sourceSkillId() != null) {
            candidate.setSourceSkillId(command.sourceSkillId());
        }
        if (command.sourceVersionId() != null) {
            candidate.setSourceVersionId(command.sourceVersionId());
        }
        if (command.actorId() != null && !command.actorId().isBlank()) {
            candidate.setCreatedBy(command.actorId());
        }
        return skillCandidateRepository.save(candidate);
    }

    @Transactional
    public SkillCandidate transitionState(Long candidateId, String promotionState) {
        SkillCandidate candidate = getCandidate(candidateId);
        candidate.setPromotionState(normalizeState(promotionState, candidate.getPromotionState()));
        return skillCandidateRepository.save(candidate);
    }

    @Transactional
    public SkillCandidate archiveCandidate(Long candidateId) {
        SkillCandidate candidate = getCandidate(candidateId);
        candidate.setPromotionState(STATE_ARCHIVED);
        return skillCandidateRepository.save(candidate);
    }

    @Transactional
    public SkillCandidate markPublished(Long candidateId, Long publishedSkillId, Long publishedVersionId) {
        SkillCandidate candidate = getCandidate(candidateId);
        candidate.setPublishedSkillId(publishedSkillId);
        candidate.setPublishedVersionId(publishedVersionId);
        candidate.setPromotionState(STATE_PUBLISHED);
        return skillCandidateRepository.save(candidate);
    }

    private String requireText(String value, String messageCode) {
        if (value == null || value.isBlank()) {
            throw new DomainBadRequestException(messageCode);
        }
        return value.trim();
    }

    private String normalizeState(String state, String fallback) {
        if (state == null || state.isBlank()) {
            return fallback;
        }
        String normalized = state.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_STATES.contains(normalized)) {
            throw new DomainBadRequestException("candidate.state.invalid", state);
        }
        return normalized;
    }

    private String normalizeObjectJson(String json) {
        return json == null || json.isBlank() ? "{}" : json;
    }

    private String normalizeArrayJson(String json) {
        return json == null || json.isBlank() ? "[]" : json;
    }
}
