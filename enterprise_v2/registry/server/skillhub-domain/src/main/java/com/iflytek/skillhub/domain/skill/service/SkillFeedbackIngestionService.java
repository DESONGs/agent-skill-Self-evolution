package com.iflytek.skillhub.domain.skill.service;

import com.iflytek.skillhub.domain.feedback.SkillRunFeedback;
import com.iflytek.skillhub.domain.feedback.SkillRunFeedbackRepository;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVersionRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SkillFeedbackIngestionService {

    public record IngestionResult(SkillRunFeedback feedback, boolean created) {}

    private final SkillRunFeedbackRepository skillRunFeedbackRepository;
    private final SkillVersionRepository skillVersionRepository;
    private final Clock clock;

    public SkillFeedbackIngestionService(SkillRunFeedbackRepository skillRunFeedbackRepository,
                                         SkillVersionRepository skillVersionRepository,
                                         Clock clock) {
        this.skillRunFeedbackRepository = skillRunFeedbackRepository;
        this.skillVersionRepository = skillVersionRepository;
        this.clock = clock;
    }

    @Transactional
    public IngestionResult ingest(String dedupeKey,
                                  String feedbackSource,
                                  String subjectType,
                                  Long skillId,
                                  Long skillVersionId,
                                  Long skillActionId,
                                  Long skillCandidateId,
                                  Long environmentProfileId,
                                  String sourceRunId,
                                  String feedbackType,
                                  Boolean success,
                                  Integer rating,
                                  Long latencyMs,
                                  String errorCode,
                                  String payloadJson,
                                  Instant observedAt,
                                  String actorId) {
        validate(dedupeKey, feedbackSource, subjectType, feedbackType);

        SkillRunFeedback existing = skillRunFeedbackRepository.findByDedupeKey(dedupeKey).orElse(null);
        if (existing != null) {
            return new IngestionResult(existing, false);
        }

        Long normalizedSkillId = resolveSkillId(skillId, skillVersionId);
        Instant normalizedObservedAt = observedAt != null ? observedAt : Instant.now(clock);
        String normalizedPayloadJson = normalizePayload(payloadJson);

        SkillRunFeedback created = skillRunFeedbackRepository.save(
                new SkillRunFeedback(
                        dedupeKey,
                        feedbackSource,
                        subjectType,
                        normalizedSkillId,
                        skillVersionId,
                        skillActionId,
                        skillCandidateId,
                        environmentProfileId,
                        sourceRunId,
                        feedbackType,
                        success,
                        rating,
                        latencyMs,
                        errorCode,
                        normalizedPayloadJson,
                        normalizedObservedAt,
                        actorId
                )
        );
        return new IngestionResult(created, true);
    }

    private void validate(String dedupeKey, String feedbackSource, String subjectType, String feedbackType) {
        if (dedupeKey == null || dedupeKey.isBlank()) {
            throw new DomainBadRequestException("feedback.dedupe_key.required");
        }
        if (feedbackSource == null || feedbackSource.isBlank()) {
            throw new DomainBadRequestException("feedback.source.required");
        }
        if (subjectType == null || subjectType.isBlank()) {
            throw new DomainBadRequestException("feedback.subject_type.required");
        }
        if (feedbackType == null || feedbackType.isBlank()) {
            throw new DomainBadRequestException("feedback.type.required");
        }
    }

    private Long resolveSkillId(Long skillId, Long skillVersionId) {
        if (skillId != null) {
            if (skillVersionId != null) {
                SkillVersion version = skillVersionRepository.findById(skillVersionId)
                        .orElseThrow(() -> new DomainBadRequestException("feedback.skill_version.not_found", skillVersionId));
                if (!Objects.equals(version.getSkillId(), skillId)) {
                    throw new DomainBadRequestException("feedback.skill_version.mismatch", skillVersionId, skillId);
                }
            }
            return skillId;
        }
        if (skillVersionId == null) {
            return null;
        }
        SkillVersion version = skillVersionRepository.findById(skillVersionId)
                .orElseThrow(() -> new DomainBadRequestException("feedback.skill_version.not_found", skillVersionId));
        return version.getSkillId();
    }

    private String normalizePayload(String payloadJson) {
        if (payloadJson == null || payloadJson.isBlank()) {
            return "{}";
        }
        return payloadJson;
    }
}

