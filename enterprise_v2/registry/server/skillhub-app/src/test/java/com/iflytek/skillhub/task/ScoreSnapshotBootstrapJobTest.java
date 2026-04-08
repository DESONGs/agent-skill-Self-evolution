package com.iflytek.skillhub.task;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.search.event.SearchIndexSyncEvent;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;

@ExtendWith(MockitoExtension.class)
class ScoreSnapshotBootstrapJobTest {

    @Mock
    private SkillScoreSnapshotService skillScoreSnapshotService;
    @Mock
    private ApplicationEventPublisher eventPublisher;

    @Test
    void bootstrapSnapshots_shouldDelegateToSnapshotServiceAndPublishRebuildEvents() {
        ScoreSnapshotBootstrapJob job = new ScoreSnapshotBootstrapJob(skillScoreSnapshotService, eventPublisher);
        when(skillScoreSnapshotService.bootstrapMissingSnapshotsDetailed())
                .thenReturn(new SkillScoreSnapshotService.SnapshotRefreshResult(3, List.of(1L, 2L, 3L)));

        job.bootstrapSnapshots();

        verify(skillScoreSnapshotService).bootstrapMissingSnapshotsDetailed();
        verify(eventPublisher, org.mockito.Mockito.times(3))
                .publishEvent(org.mockito.ArgumentMatchers.any(SearchIndexSyncEvent.class));
    }
}
