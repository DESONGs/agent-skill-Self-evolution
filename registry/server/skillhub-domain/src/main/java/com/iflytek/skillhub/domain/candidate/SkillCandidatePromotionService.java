package com.iflytek.skillhub.domain.candidate;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.service.SkillPublishService;
import com.iflytek.skillhub.domain.skill.validation.PackageEntry;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service("candidateIngressSkillCandidatePromotionService")
public class SkillCandidatePromotionService {

    public record PublishCommand(
            String namespaceSlug,
            String publisherId,
            SkillVisibility visibility,
            Set<String> platformRoles
    ) {}

    public record CandidatePublishResult(
            SkillCandidate candidate,
            SkillPublishService.PublishResult publishResult,
            SkillPromotionDecision decision,
            Instant publishedAt
    ) {}

    private final SkillCandidateService skillCandidateService;
    private final SkillPromotionDecisionService skillPromotionDecisionService;
    private final SkillPublishService skillPublishService;
    private final SkillScoreSnapshotService skillScoreSnapshotService;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    public SkillCandidatePromotionService(SkillCandidateService skillCandidateService,
                                          SkillPromotionDecisionService skillPromotionDecisionService,
                                          SkillPublishService skillPublishService,
                                          SkillScoreSnapshotService skillScoreSnapshotService,
                                          ObjectMapper objectMapper,
                                          Clock clock) {
        this.skillCandidateService = skillCandidateService;
        this.skillPromotionDecisionService = skillPromotionDecisionService;
        this.skillPublishService = skillPublishService;
        this.skillScoreSnapshotService = skillScoreSnapshotService;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    @Transactional
    public CandidatePublishResult publishCandidate(Long candidateId, PublishCommand command) {
        SkillCandidate candidate = skillCandidateService.getCandidate(candidateId);
        SkillPromotionDecision latestDecision = skillPromotionDecisionService.latestDecision(candidateId)
                .orElseThrow(() -> new DomainBadRequestException("candidate.publish.decision.required", candidateId));
        if (!"PROMOTE".equals(latestDecision.getDecision())) {
            throw new DomainBadRequestException("candidate.publish.decision.invalid", latestDecision.getDecision());
        }
        if (command.namespaceSlug() == null || command.namespaceSlug().isBlank()) {
            throw new DomainBadRequestException("candidate.publish.namespace.required");
        }
        if (command.publisherId() == null || command.publisherId().isBlank()) {
            throw new DomainBadRequestException("candidate.publish.publisher.required");
        }

        SkillPublishService.PublishResult publishResult = skillPublishService.publishFromEntries(
                command.namespaceSlug().trim(),
                extractPackageEntries(candidate.getCandidateSpecJson()),
                command.publisherId().trim(),
                command.visibility() != null ? command.visibility() : SkillVisibility.PRIVATE,
                command.platformRoles() != null ? command.platformRoles() : Set.of()
        );
        SkillCandidate publishedCandidate = skillCandidateService.markPublished(
                candidateId,
                publishResult.skillId(),
                publishResult.version().getId()
        );
        skillScoreSnapshotService.refreshSkillSnapshot(publishResult.skillId());
        return new CandidatePublishResult(
                publishedCandidate,
                publishResult,
                latestDecision,
                Instant.now(clock)
        );
    }

    private List<PackageEntry> extractPackageEntries(String candidateSpecJson) {
        try {
            JsonNode root = objectMapper.readTree(candidateSpecJson);
            JsonNode entriesNode = resolveEntriesNode(root);
            if (entriesNode == null || !entriesNode.isArray() || entriesNode.isEmpty()) {
                throw new DomainBadRequestException("candidate.publish.entries.required");
            }
            List<PackageEntry> entries = new ArrayList<>();
            for (JsonNode entryNode : entriesNode) {
                String path = readRequiredText(entryNode, "path", "candidate.publish.entry.path.required");
                byte[] content = readEntryContent(entryNode);
                String contentType = readText(entryNode, "contentType", "application/octet-stream");
                entries.add(new PackageEntry(path, content, content.length, contentType));
            }
            return entries;
        } catch (DomainBadRequestException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new DomainBadRequestException("candidate.publish.spec.invalid", exception.getMessage());
        }
    }

    private JsonNode resolveEntriesNode(JsonNode root) {
        if (root == null || root.isNull()) {
            return null;
        }
        if (root.has("packageEntries")) {
            return root.get("packageEntries");
        }
        if (root.has("package") && root.get("package").has("entries")) {
            return root.get("package").get("entries");
        }
        if (root.has("entries")) {
            return root.get("entries");
        }
        return null;
    }

    private byte[] readEntryContent(JsonNode entryNode) {
        String contentBase64 = readText(entryNode, "contentBase64", null);
        if (contentBase64 != null && !contentBase64.isBlank()) {
            return Base64.getDecoder().decode(contentBase64);
        }
        String content = readText(entryNode, "content", null);
        if (content != null) {
            String encoding = readText(entryNode, "encoding", "text").toUpperCase(Locale.ROOT);
            if ("BASE64".equals(encoding)) {
                return Base64.getDecoder().decode(content);
            }
            return content.getBytes(StandardCharsets.UTF_8);
        }
        String contentText = readText(entryNode, "contentText", null);
        if (contentText != null) {
            return contentText.getBytes(StandardCharsets.UTF_8);
        }
        throw new DomainBadRequestException("candidate.publish.entry.content.required");
    }

    private String readRequiredText(JsonNode node, String fieldName, String messageCode) {
        String value = readText(node, fieldName, null);
        if (value == null || value.isBlank()) {
            throw new DomainBadRequestException(messageCode);
        }
        return value;
    }

    private String readText(JsonNode node, String fieldName, String fallback) {
        JsonNode field = node.get(fieldName);
        if (field == null || field.isNull()) {
            return fallback;
        }
        String text = field.asText();
        return text == null || text.isBlank() ? fallback : text;
    }
}
