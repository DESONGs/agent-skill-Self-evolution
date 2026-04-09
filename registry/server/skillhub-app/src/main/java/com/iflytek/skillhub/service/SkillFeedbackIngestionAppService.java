package com.iflytek.skillhub.service;

import com.iflytek.skillhub.domain.feedback.SkillRunFeedback;
import com.iflytek.skillhub.domain.skill.service.SkillFeedbackIngestionService;
import com.iflytek.skillhub.dto.internal.SkillFeedbackIngestionRequest;
import com.iflytek.skillhub.dto.internal.SkillFeedbackIngestionResponse;
import org.springframework.stereotype.Service;

@Service
public class SkillFeedbackIngestionAppService {

    private final SkillFeedbackIngestionService skillFeedbackIngestionService;

    public SkillFeedbackIngestionAppService(SkillFeedbackIngestionService skillFeedbackIngestionService) {
        this.skillFeedbackIngestionService = skillFeedbackIngestionService;
    }

    public SkillFeedbackIngestionResponse ingest(SkillFeedbackIngestionRequest request) {
        SkillFeedbackIngestionService.IngestionResult result = skillFeedbackIngestionService.ingest(
                request.dedupeKey(),
                request.feedbackSource(),
                request.subjectType(),
                request.skillId(),
                request.skillVersionId(),
                request.skillActionId(),
                request.skillCandidateId(),
                request.environmentProfileId(),
                request.sourceRunId(),
                request.feedbackType(),
                request.success(),
                request.rating(),
                request.latencyMs(),
                request.errorCode(),
                request.payloadJson(),
                request.observedAt(),
                request.actorId()
        );
        return toResponse(result.feedback(), result.created());
    }

    private SkillFeedbackIngestionResponse toResponse(SkillRunFeedback feedback, boolean created) {
        return new SkillFeedbackIngestionResponse(
                feedback.getId(),
                feedback.getDedupeKey(),
                feedback.getSkillId(),
                feedback.getSkillVersionId(),
                feedback.getFeedbackType(),
                created,
                feedback.getObservedAt(),
                feedback.getIngestedAt()
        );
    }
}
