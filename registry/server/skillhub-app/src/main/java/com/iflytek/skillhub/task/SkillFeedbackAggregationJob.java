package com.iflytek.skillhub.task;

import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.search.event.SearchIndexAction;
import com.iflytek.skillhub.search.event.SearchIndexSyncEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component("feedbackSkillAggregationTask")
public class SkillFeedbackAggregationJob {

    private static final Logger logger = LoggerFactory.getLogger(SkillFeedbackAggregationJob.class);

    private final SkillScoreSnapshotService skillScoreSnapshotService;
    private final ApplicationEventPublisher eventPublisher;

    public SkillFeedbackAggregationJob(SkillScoreSnapshotService skillScoreSnapshotService,
                                       ApplicationEventPublisher eventPublisher) {
        this.skillScoreSnapshotService = skillScoreSnapshotService;
        this.eventPublisher = eventPublisher;
    }

    @Scheduled(
            fixedDelayString = "${skillhub.feedback.snapshot.aggregate-delay-ms:300000}",
            initialDelayString = "${skillhub.feedback.snapshot.aggregate-initial-delay-ms:60000}"
    )
    public void aggregateSnapshots() {
        SkillScoreSnapshotService.SnapshotRefreshResult result = skillScoreSnapshotService.refreshAllSnapshots();
        result.skillIds().forEach(skillId ->
                eventPublisher.publishEvent(new SearchIndexSyncEvent(skillId, SearchIndexAction.REBUILD)));
        if (result.refreshedCount() > 0) {
            logger.info("Refreshed {} skill score snapshots", result.refreshedCount());
        }
    }
}
