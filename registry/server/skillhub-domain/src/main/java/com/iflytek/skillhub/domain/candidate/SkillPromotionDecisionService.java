package com.iflytek.skillhub.domain.candidate;

import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service("candidateIngressSkillPromotionDecisionService")
public class SkillPromotionDecisionService {

    private static final Set<String> ALLOWED_DECISIONS = Set.of("PROMOTE", "REJECT", "HOLD", "DEMOTE");
    private static final Set<String> ALLOWED_MODES = Set.of("AUTOMATIC", "HUMAN_REVIEW", "POLICY");

    public record DecisionCommand(
            String decision,
            String decisionMode,
            String reasonsJson,
            String scoresJson,
            String evidenceIndexKey,
            String decidedBy,
            Instant decidedAt
    ) {}

    private final SkillCandidateService skillCandidateService;
    private final SkillPromotionDecisionRepository skillPromotionDecisionRepository;
    private final Clock clock;

    public SkillPromotionDecisionService(SkillCandidateService skillCandidateService,
                                         SkillPromotionDecisionRepository skillPromotionDecisionRepository,
                                         Clock clock) {
        this.skillCandidateService = skillCandidateService;
        this.skillPromotionDecisionRepository = skillPromotionDecisionRepository;
        this.clock = clock;
    }

    @Transactional
    public SkillPromotionDecision appendDecision(Long candidateId, DecisionCommand command) {
        skillCandidateService.getCandidate(candidateId);
        String decision = normalizeDecision(command.decision());
        String decisionMode = normalizeMode(command.decisionMode());
        SkillPromotionDecision created = skillPromotionDecisionRepository.save(new SkillPromotionDecision(
                candidateId,
                decision,
                decisionMode,
                command.reasonsJson() == null || command.reasonsJson().isBlank() ? "[]" : command.reasonsJson(),
                command.scoresJson() == null || command.scoresJson().isBlank() ? "{}" : command.scoresJson(),
                command.evidenceIndexKey(),
                command.decidedBy(),
                command.decidedAt() != null ? command.decidedAt() : Instant.now(clock)
        ));
        skillCandidateService.transitionState(candidateId, mapState(decision));
        return created;
    }

    @Transactional(readOnly = true)
    public List<SkillPromotionDecision> listDecisions(Long candidateId) {
        skillCandidateService.getCandidate(candidateId);
        return skillPromotionDecisionRepository.findBySkillCandidateIdOrderByDecidedAtDesc(candidateId);
    }

    @Transactional(readOnly = true)
    public Optional<SkillPromotionDecision> latestDecision(Long candidateId) {
        return listDecisions(candidateId).stream().findFirst();
    }

    private String normalizeDecision(String value) {
        if (value == null || value.isBlank()) {
            throw new DomainBadRequestException("candidate.decision.required");
        }
        String normalized = value.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_DECISIONS.contains(normalized)) {
            throw new DomainBadRequestException("candidate.decision.invalid", value);
        }
        return normalized;
    }

    private String normalizeMode(String value) {
        if (value == null || value.isBlank()) {
            throw new DomainBadRequestException("candidate.decision_mode.required");
        }
        String normalized = value.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_MODES.contains(normalized)) {
            throw new DomainBadRequestException("candidate.decision_mode.invalid", value);
        }
        return normalized;
    }

    private String mapState(String decision) {
        return switch (decision) {
            case "PROMOTE" -> SkillCandidateService.STATE_PROMOTION_PENDING;
            case "HOLD" -> SkillCandidateService.STATE_EVALUATED;
            case "REJECT", "DEMOTE" -> SkillCandidateService.STATE_REJECTED;
            default -> SkillCandidateService.STATE_CREATED;
        };
    }
}
