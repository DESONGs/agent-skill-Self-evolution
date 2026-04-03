package com.iflytek.skillhub.domain.skill.service;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.namespace.SlugValidator;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SkillCandidateService {

    public record CreateCommand(
            String candidateKey,
            String candidateSlug,
            String candidateSpecJson,
            String sourceKind,
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
            String createdBy
    ) {
    }

    private final SkillCandidateRepository skillCandidateRepository;

    public SkillCandidateService(SkillCandidateRepository skillCandidateRepository) {
        this.skillCandidateRepository = skillCandidateRepository;
    }

    @Transactional
    public SkillCandidate create(CreateCommand command) {
        String candidateKey = normalizeCandidateKey(command.candidateKey(), command.candidateSlug(), command.problemStatement());
        skillCandidateRepository.findByCandidateKey(candidateKey)
                .ifPresent(existing -> {
                    throw new DomainBadRequestException("candidate.key.exists", candidateKey);
                });

        String candidateSlug = normalizeCandidateSlug(command.candidateSlug(), command.problemStatement(), candidateKey);
        SkillCandidate candidate = new SkillCandidate(
                candidateKey,
                candidateSlug,
                normalizeText(command.sourceKind(), "MANUAL"),
                normalizeJson(command.candidateSpecJson(), "{}"),
                normalizeJson(command.sourceRefsJson(), "[]"),
                blankToNull(command.problemStatement()),
                blankToNull(command.targetUser()),
                blankToNull(command.skillBoundary()),
                blankToNull(command.triggerDescription()),
                normalizeJson(command.antiTriggersJson(), "[]"),
                blankToNull(command.defaultActionId()),
                normalizeJson(command.governanceJson(), "{}"),
                normalizeJson(command.metricsJson(), "{}"),
                blankToNull(command.generatedBundleKey()),
                blankToNull(command.generatedManifestKey()),
                blankToNull(command.reportIndexKey()),
                blankToNull(command.latestLabRunId()),
                normalizeText(command.promotionState(), "CREATED"),
                command.sourceSkillId(),
                command.sourceVersionId(),
                null,
                null,
                blankToNull(command.createdBy())
        );
        return skillCandidateRepository.save(candidate);
    }

    @Transactional(readOnly = true)
    public List<SkillCandidate> list(String promotionState) {
        List<SkillCandidate> candidates = promotionState == null || promotionState.isBlank()
                ? skillCandidateRepository.findAllByOrderByUpdatedAtDesc()
                : skillCandidateRepository.findByPromotionState(normalizeText(promotionState, null));
        return candidates.stream()
                .sorted(Comparator.comparing(SkillCandidate::getUpdatedAt).reversed())
                .toList();
    }

    @Transactional(readOnly = true)
    public SkillCandidate get(Long candidateId) {
        return skillCandidateRepository.findById(candidateId)
                .orElseThrow(() -> new DomainBadRequestException("candidate.not_found", candidateId));
    }

    @Transactional
    public SkillCandidate save(SkillCandidate candidate) {
        return skillCandidateRepository.save(candidate);
    }

    private String normalizeCandidateKey(String requestedKey, String candidateSlug, String problemStatement) {
        String normalized = blankToNull(requestedKey);
        if (normalized == null) {
            String seed = blankToNull(candidateSlug);
            if (seed == null) {
                seed = blankToNull(problemStatement);
            }
            if (seed == null) {
                seed = "candidate";
            }
            normalized = SlugValidator.slugify(seed) + "-" + UUID.randomUUID().toString().substring(0, 8);
        }
        return normalized.trim().toLowerCase(Locale.ROOT);
    }

    private String normalizeCandidateSlug(String requestedSlug, String problemStatement, String candidateKey) {
        String seed = blankToNull(requestedSlug);
        if (seed == null) {
            seed = blankToNull(problemStatement);
        }
        if (seed == null) {
            seed = candidateKey;
        }
        return SlugValidator.slugify(seed);
    }

    private String normalizeJson(String value, String defaultValue) {
        return value == null || value.isBlank() ? defaultValue : value;
    }

    private String normalizeText(String value, String defaultValue) {
        return value == null || value.isBlank() ? defaultValue : value.trim().toUpperCase(Locale.ROOT);
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
