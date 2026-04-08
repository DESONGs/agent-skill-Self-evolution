package com.iflytek.skillhub.task;

import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.search.event.SearchIndexAction;
import com.iflytek.skillhub.search.event.SearchIndexSyncEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component("feedbackScoreSnapshotBootstrapTask")
public class ScoreSnapshotBootstrapJob {

    private static final Logger logger = LoggerFactory.getLogger(ScoreSnapshotBootstrapJob.class);

    private final SkillScoreSnapshotService skillScoreSnapshotService;
    private final ApplicationEventPublisher eventPublisher;

    public ScoreSnapshotBootstrapJob(SkillScoreSnapshotService skillScoreSnapshotService,
                                     ApplicationEventPublisher eventPublisher) {
        this.skillScoreSnapshotService = skillScoreSnapshotService;
        this.eventPublisher = eventPublisher;
    }

    @Scheduled(
            fixedDelayString = "${skillhub.feedback.snapshot.bootstrap-delay-ms:3600000}",
            initialDelayString = "${skillhub.feedback.snapshot.bootstrap-initial-delay-ms:120000}"
    )
    public void bootstrapSnapshots() {
        SkillScoreSnapshotService.SnapshotRefreshResult result =
                skillScoreSnapshotService.bootstrapMissingSnapshotsDetailed();
        result.skillIds().forEach(skillId ->
                eventPublisher.publishEvent(new SearchIndexSyncEvent(skillId, SearchIndexAction.REBUILD)));
        if (result.refreshedCount() > 0) {
            logger.info("Bootstrapped {} missing skill score snapshots", result.refreshedCount());
        }
    }
}
