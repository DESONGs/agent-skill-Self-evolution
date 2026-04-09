package com.iflytek.skillhub.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecision;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.service.SkillCandidatePromotionService;
import com.iflytek.skillhub.domain.skill.service.SkillCandidateService;
import com.iflytek.skillhub.domain.skill.service.SkillPromotionDecisionService;
import com.iflytek.skillhub.dto.internal.SkillCandidateCreateRequest;
import com.iflytek.skillhub.dto.internal.SkillCandidateDetailResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidatePublishRequest;
import com.iflytek.skillhub.dto.internal.SkillCandidatePublishResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidateRequest;
import com.iflytek.skillhub.dto.internal.SkillCandidateResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidateSummaryResponse;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionCreateRequest;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionRequest;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionResponse;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class SkillCandidateAppService {

    private final SkillCandidateService skillCandidateService;
    private final SkillPromotionDecisionService skillPromotionDecisionService;
    private final SkillCandidatePromotionService skillCandidatePromotionService;
    private final ObjectMapper objectMapper;

    public SkillCandidateAppService(SkillCandidateService skillCandidateService,
                                    SkillPromotionDecisionService skillPromotionDecisionService,
                                    SkillCandidatePromotionService skillCandidatePromotionService,
                                    ObjectMapper objectMapper) {
        this.skillCandidateService = skillCandidateService;
        this.skillPromotionDecisionService = skillPromotionDecisionService;
        this.skillCandidatePromotionService = skillCandidatePromotionService;
        this.objectMapper = objectMapper;
    }

    public SkillCandidateDetailResponse create(SkillCandidateCreateRequest request, String actorId) {
        SkillCandidate candidate = skillCandidateService.create(new SkillCandidateService.CreateCommand(
                request.candidateKey(),
                request.candidateSlug(),
                request.candidateSpecJson(),
                request.sourceKind(),
                request.sourceRefsJson(),
                request.problemStatement(),
                request.targetUser(),
                request.skillBoundary(),
                request.triggerDescription(),
                request.antiTriggersJson(),
                request.defaultActionId(),
                request.governanceJson(),
                request.metricsJson(),
                request.generatedBundleKey(),
                request.generatedManifestKey(),
                request.reportIndexKey(),
                request.latestLabRunId(),
                request.promotionState(),
                request.sourceSkillId(),
                request.sourceVersionId(),
                request.createdBy() != null && !request.createdBy().isBlank() ? request.createdBy() : actorId
        ));
        return toDetail(candidate, List.of());
    }

    public SkillCandidateResponse createCandidate(SkillCandidateRequest request, String actorId) {
        return toResponse(skillCandidateService.create(new SkillCandidateService.CreateCommand(
                request.candidateKey(),
                request.candidateSlug(),
                writeJson(request.candidateSpec(), "{}"),
                request.sourceKind(),
                writeJson(request.sourceRefs(), "[]"),
                request.problemStatement(),
                request.targetUser(),
                request.skillBoundary(),
                request.triggerDescription(),
                writeJson(request.antiTriggers(), "[]"),
                request.defaultActionId(),
                writeJson(request.governance(), "{}"),
                writeJson(request.metrics(), "{}"),
                request.generatedBundleKey(),
                request.generatedManifestKey(),
                request.reportIndexKey(),
                request.latestLabRunId(),
                request.promotionState(),
                request.sourceSkillId(),
                request.sourceVersionId(),
                request.actorId() != null && !request.actorId().isBlank() ? request.actorId() : actorId
        )));
    }

    public List<SkillCandidateSummaryResponse> list(String promotionState) {
        return skillCandidateService.list(promotionState).stream()
                .map(this::toSummary)
                .toList();
    }

    public List<SkillCandidateResponse> listCandidates(String promotionState) {
        return skillCandidateService.list(promotionState).stream()
                .map(this::toResponse)
                .toList();
    }

    public SkillCandidateDetailResponse get(Long candidateId) {
        SkillCandidate candidate = skillCandidateService.get(candidateId);
        List<SkillPromotionDecisionResponse> decisions = skillPromotionDecisionService.listByCandidateId(candidateId).stream()
                .map(this::toDecisionResponse)
                .toList();
        return toDetail(candidate, decisions);
    }

    public SkillCandidateResponse getCandidate(Long candidateId) {
        return toResponse(skillCandidateService.get(candidateId));
    }

    public SkillCandidateDetailResponse update(Long candidateId,
                                               SkillCandidateCreateRequest request,
                                               String actorId) {
        SkillCandidate candidate = skillCandidateService.get(candidateId);
        if (request.candidateSlug() != null && !request.candidateSlug().isBlank()) {
            candidate.setCandidateSlug(request.candidateSlug().trim());
        }
        if (request.candidateSpecJson() != null) {
            candidate.setCandidateSpecJson(request.candidateSpecJson());
        }
        if (request.sourceKind() != null && !request.sourceKind().isBlank()) {
            candidate.setSourceKind(request.sourceKind().trim().toUpperCase());
        }
        if (request.sourceRefsJson() != null) {
            candidate.setSourceRefsJson(request.sourceRefsJson());
        }
        if (request.problemStatement() != null) {
            candidate.setProblemStatement(blankToNull(request.problemStatement()));
        }
        if (request.targetUser() != null) {
            candidate.setTargetUser(blankToNull(request.targetUser()));
        }
        if (request.skillBoundary() != null) {
            candidate.setSkillBoundary(blankToNull(request.skillBoundary()));
        }
        if (request.triggerDescription() != null) {
            candidate.setTriggerDescription(blankToNull(request.triggerDescription()));
        }
        if (request.antiTriggersJson() != null) {
            candidate.setAntiTriggersJson(request.antiTriggersJson());
        }
        if (request.defaultActionId() != null) {
            candidate.setDefaultActionId(blankToNull(request.defaultActionId()));
        }
        if (request.governanceJson() != null) {
            candidate.setGovernanceJson(request.governanceJson());
        }
        if (request.metricsJson() != null) {
            candidate.setMetricsJson(request.metricsJson());
        }
        if (request.generatedBundleKey() != null) {
            candidate.setGeneratedBundleKey(blankToNull(request.generatedBundleKey()));
        }
        if (request.generatedManifestKey() != null) {
            candidate.setGeneratedManifestKey(blankToNull(request.generatedManifestKey()));
        }
        if (request.reportIndexKey() != null) {
            candidate.setReportIndexKey(blankToNull(request.reportIndexKey()));
        }
        if (request.latestLabRunId() != null) {
            candidate.setLatestLabRunId(blankToNull(request.latestLabRunId()));
        }
        if (request.promotionState() != null && !request.promotionState().isBlank()) {
            candidate.setPromotionState(request.promotionState().trim().toUpperCase());
        }
        if (request.sourceSkillId() != null) {
            candidate.setSourceSkillId(request.sourceSkillId());
        }
        if (request.sourceVersionId() != null) {
            candidate.setSourceVersionId(request.sourceVersionId());
        }
        if ((request.createdBy() != null && !request.createdBy().isBlank()) || (actorId != null && !actorId.isBlank())) {
            candidate.setCreatedBy(request.createdBy() != null && !request.createdBy().isBlank() ? request.createdBy().trim() : actorId);
        }
        SkillCandidate saved = skillCandidateService.save(candidate);
        return get(saved.getId());
    }

    public SkillCandidateResponse updateCandidate(Long candidateId, SkillCandidateRequest request, String actorId) {
        SkillCandidate candidate = skillCandidateService.get(candidateId);
        if (request.candidateSlug() != null) {
            candidate.setCandidateSlug(request.candidateSlug());
        }
        if (request.candidateSpec() != null) {
            candidate.setCandidateSpecJson(writeJson(request.candidateSpec(), "{}"));
        }
        if (request.sourceKind() != null) {
            candidate.setSourceKind(request.sourceKind());
        }
        if (request.sourceRefs() != null) {
            candidate.setSourceRefsJson(writeJson(request.sourceRefs(), "[]"));
        }
        if (request.problemStatement() != null) {
            candidate.setProblemStatement(request.problemStatement());
        }
        if (request.targetUser() != null) {
            candidate.setTargetUser(request.targetUser());
        }
        if (request.skillBoundary() != null) {
            candidate.setSkillBoundary(request.skillBoundary());
        }
        if (request.triggerDescription() != null) {
            candidate.setTriggerDescription(request.triggerDescription());
        }
        if (request.antiTriggers() != null) {
            candidate.setAntiTriggersJson(writeJson(request.antiTriggers(), "[]"));
        }
        if (request.defaultActionId() != null) {
            candidate.setDefaultActionId(request.defaultActionId());
        }
        if (request.governance() != null) {
            candidate.setGovernanceJson(writeJson(request.governance(), "{}"));
        }
        if (request.metrics() != null) {
            candidate.setMetricsJson(writeJson(request.metrics(), "{}"));
        }
        if (request.generatedBundleKey() != null) {
            candidate.setGeneratedBundleKey(request.generatedBundleKey());
        }
        if (request.generatedManifestKey() != null) {
            candidate.setGeneratedManifestKey(request.generatedManifestKey());
        }
        if (request.reportIndexKey() != null) {
            candidate.setReportIndexKey(request.reportIndexKey());
        }
        if (request.latestLabRunId() != null) {
            candidate.setLatestLabRunId(request.latestLabRunId());
        }
        if (request.promotionState() != null) {
            candidate.setPromotionState(request.promotionState());
        }
        if (request.sourceSkillId() != null) {
            candidate.setSourceSkillId(request.sourceSkillId());
        }
        if (request.sourceVersionId() != null) {
            candidate.setSourceVersionId(request.sourceVersionId());
        }
        if (request.actorId() != null) {
            candidate.setCreatedBy(request.actorId());
        } else if (actorId != null) {
            candidate.setCreatedBy(actorId);
        }
        return toResponse(skillCandidateService.save(candidate));
    }

    public SkillCandidateDetailResponse archive(Long candidateId) {
        SkillCandidate candidate = skillCandidateService.get(candidateId);
        candidate.setPromotionState("ARCHIVED");
        SkillCandidate saved = skillCandidateService.save(candidate);
        return get(saved.getId());
    }

    public SkillCandidateResponse archiveCandidate(Long candidateId) {
        SkillCandidate candidate = skillCandidateService.get(candidateId);
        candidate.setPromotionState("ARCHIVED");
        return toResponse(skillCandidateService.save(candidate));
    }

    public SkillPromotionDecisionResponse createDecision(Long candidateId,
                                                         SkillPromotionDecisionCreateRequest request,
                                                         String actorId) {
        SkillPromotionDecision decision = skillPromotionDecisionService.createDecision(
                candidateId,
                new SkillPromotionDecisionService.CreateDecisionCommand(
                        request.decision(),
                        request.decisionMode(),
                        request.reasonsJson(),
                        request.scoresJson(),
                        request.evidenceIndexKey(),
                        request.decidedBy() != null && !request.decidedBy().isBlank() ? request.decidedBy() : actorId,
                        request.decidedAt()
                )
        );
        return toDecisionResponse(decision);
    }

    public SkillPromotionDecisionResponse appendDecision(Long candidateId,
                                                         SkillPromotionDecisionRequest request,
                                                         String actorId) {
        return toDecisionResponse(skillPromotionDecisionService.createDecision(
                candidateId,
                new SkillPromotionDecisionService.CreateDecisionCommand(
                        request.decision(),
                        request.decisionMode(),
                        writeJson(request.reasons(), "[]"),
                        writeJson(request.scores(), "{}"),
                        request.evidenceIndexKey(),
                        request.decidedBy() != null && !request.decidedBy().isBlank() ? request.decidedBy() : actorId,
                        request.decidedAt()
                )
        ));
    }

    public SkillCandidatePublishResponse publish(Long candidateId,
                                                 SkillCandidatePublishRequest request,
                                                 PlatformPrincipal principal) {
        SkillCandidatePromotionService.CandidatePublishResult result = skillCandidatePromotionService.publish(
                candidateId,
                request.namespace(),
                request.visibility() == null || request.visibility().isBlank()
                        ? SkillVisibility.PUBLIC
                        : SkillVisibility.valueOf(request.visibility().trim().toUpperCase()),
                principal.userId(),
                principal.platformRoles()
        );
        return new SkillCandidatePublishResponse(
                result.candidate().getId(),
                result.candidate().getPromotionState(),
                result.skillId(),
                result.version().getId(),
                request.namespace(),
                result.slug(),
                result.version().getVersion(),
                result.version().getStatus().name()
        );
    }

    public SkillCandidatePublishResponse publishCandidate(Long candidateId,
                                                          SkillCandidatePublishRequest request,
                                                          String actorId) {
        return publish(candidateId, request, new PlatformPrincipal(
                actorId,
                actorId,
                null,
                "",
                "internal",
                Set.of("USER")
        ));
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private SkillCandidateSummaryResponse toSummary(SkillCandidate candidate) {
        return new SkillCandidateSummaryResponse(
                candidate.getId(),
                candidate.getCandidateKey(),
                candidate.getCandidateSlug(),
                candidate.getSourceKind(),
                candidate.getProblemStatement(),
                candidate.getTargetUser(),
                candidate.getPromotionState(),
                candidate.getPublishedSkillId(),
                candidate.getPublishedVersionId(),
                candidate.getCreatedBy(),
                candidate.getCreatedAt(),
                candidate.getUpdatedAt()
        );
    }

    private SkillCandidateDetailResponse toDetail(SkillCandidate candidate,
                                                  List<SkillPromotionDecisionResponse> decisions) {
        return new SkillCandidateDetailResponse(
                candidate.getId(),
                candidate.getCandidateKey(),
                candidate.getCandidateSlug(),
                candidate.getCandidateSpecJson(),
                candidate.getSourceKind(),
                candidate.getSourceRefsJson(),
                candidate.getProblemStatement(),
                candidate.getTargetUser(),
                candidate.getSkillBoundary(),
                candidate.getTriggerDescription(),
                candidate.getAntiTriggersJson(),
                candidate.getDefaultActionId(),
                candidate.getGovernanceJson(),
                candidate.getMetricsJson(),
                candidate.getGeneratedBundleKey(),
                candidate.getGeneratedManifestKey(),
                candidate.getReportIndexKey(),
                candidate.getLatestLabRunId(),
                candidate.getPromotionState(),
                candidate.getSourceSkillId(),
                candidate.getSourceVersionId(),
                candidate.getPublishedSkillId(),
                candidate.getPublishedVersionId(),
                candidate.getCreatedBy(),
                candidate.getCreatedAt(),
                candidate.getUpdatedAt(),
                decisions
        );
    }

    private SkillPromotionDecisionResponse toDecisionResponse(SkillPromotionDecision decision) {
        return new SkillPromotionDecisionResponse(
                decision.getId(),
                decision.getSkillCandidateId(),
                decision.getDecision(),
                decision.getDecisionMode(),
                decision.getReasonsJson(),
                decision.getScoresJson(),
                decision.getEvidenceIndexKey(),
                decision.getDecidedBy(),
                decision.getDecidedAt(),
                decision.getCreatedAt()
        );
    }

    private SkillCandidateResponse toResponse(SkillCandidate candidate) {
        return new SkillCandidateResponse(
                candidate.getId(),
                candidate.getCandidateKey(),
                candidate.getCandidateSlug(),
                candidate.getSourceKind(),
                readObject(candidate.getCandidateSpecJson()),
                readArray(candidate.getSourceRefsJson()),
                candidate.getProblemStatement(),
                candidate.getTargetUser(),
                candidate.getSkillBoundary(),
                candidate.getTriggerDescription(),
                readArray(candidate.getAntiTriggersJson()),
                candidate.getDefaultActionId(),
                readObject(candidate.getGovernanceJson()),
                readObject(candidate.getMetricsJson()),
                candidate.getGeneratedBundleKey(),
                candidate.getGeneratedManifestKey(),
                candidate.getReportIndexKey(),
                candidate.getLatestLabRunId(),
                candidate.getPromotionState(),
                candidate.getSourceSkillId(),
                candidate.getSourceVersionId(),
                candidate.getPublishedSkillId(),
                candidate.getPublishedVersionId(),
                candidate.getCreatedBy(),
                candidate.getCreatedAt(),
                candidate.getUpdatedAt()
        );
    }

    private String writeJson(JsonNode node, String fallback) {
        return node == null ? fallback : node.toString();
    }

    private ObjectNode readObject(String json) {
        try {
            JsonNode node = json == null || json.isBlank() ? objectMapper.createObjectNode() : objectMapper.readTree(json);
            return node instanceof ObjectNode objectNode ? objectNode : objectMapper.createObjectNode();
        } catch (Exception ex) {
            return objectMapper.createObjectNode();
        }
    }

    private ArrayNode readArray(String json) {
        try {
            JsonNode node = json == null || json.isBlank() ? objectMapper.createArrayNode() : objectMapper.readTree(json);
            return node instanceof ArrayNode arrayNode ? arrayNode : objectMapper.createArrayNode();
        } catch (Exception ex) {
            return objectMapper.createArrayNode();
        }
    }
}
