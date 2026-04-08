package com.iflytek.skillhub.domain.skill.service;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecision;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecisionRepository;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SkillPromotionDecisionService {
    private static final Set<String> ALLOWED_DECISIONS = Set.of("PROMOTE", "REJECT", "HOLD", "DEMOTE");

    public record CreateDecisionCommand(
            String decision,
            String decisionMode,
            String reasonsJson,
            String scoresJson,
            String evidenceIndexKey,
            String decidedBy,
            Instant decidedAt
    ) {
    }

    private final SkillCandidateRepository skillCandidateRepository;
    private final SkillPromotionDecisionRepository skillPromotionDecisionRepository;
    private final Clock clock;

    public SkillPromotionDecisionService(SkillCandidateRepository skillCandidateRepository,
                                         SkillPromotionDecisionRepository skillPromotionDecisionRepository,
                                         Clock clock) {
        this.skillCandidateRepository = skillCandidateRepository;
        this.skillPromotionDecisionRepository = skillPromotionDecisionRepository;
        this.clock = clock;
    }

    @Transactional
    public SkillPromotionDecision createDecision(Long candidateId, CreateDecisionCommand command) {
        SkillCandidate candidate = skillCandidateRepository.findById(candidateId)
                .orElseThrow(() -> new DomainBadRequestException("candidate.not_found", candidateId));
        String normalizedDecision = normalizeDecision(command.decision());
        SkillPromotionDecision decision = skillPromotionDecisionRepository.save(new SkillPromotionDecision(
                candidateId,
                normalizedDecision,
                normalizeText(command.decisionMode(), "HUMAN_REVIEW"),
                normalizeJson(command.reasonsJson(), "[]"),
                normalizeJson(command.scoresJson(), "{}"),
                blankToNull(command.evidenceIndexKey()),
                blankToNull(command.decidedBy()),
                command.decidedAt() != null ? command.decidedAt() : Instant.now(clock)
        ));

        candidate.setPromotionState(nextPromotionState(normalizedDecision, candidate.getPromotionState()));
        skillCandidateRepository.save(candidate);
        return decision;
    }

    @Transactional(readOnly = true)
    public List<SkillPromotionDecision> listByCandidateId(Long candidateId) {
        return skillPromotionDecisionRepository.findBySkillCandidateIdOrderByDecidedAtDesc(candidateId);
    }

    private String normalizeDecision(String decision) {
        String normalized = normalizeText(decision, null);
        if (normalized == null || !ALLOWED_DECISIONS.contains(normalized)) {
            throw new DomainBadRequestException("candidate.decision.invalid", decision);
        }
        return normalized;
    }

    private String nextPromotionState(String decision, String currentState) {
        return switch (decision) {
            case "PROMOTE" -> "PROMOTION_PENDING";
            case "REJECT" -> "REJECTED";
            case "DEMOTE" -> "SUPERSEDED";
            default -> currentState == null || currentState.isBlank() ? "EVALUATED" : currentState;
        };
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
