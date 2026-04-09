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
class SkillFeedbackAggregationJobTest {

    @Mock
    private SkillScoreSnapshotService skillScoreSnapshotService;
    @Mock
    private ApplicationEventPublisher eventPublisher;

    @Test
    void aggregateSnapshots_shouldDelegateToSnapshotServiceAndPublishRebuildEvents() {
        SkillFeedbackAggregationJob job = new SkillFeedbackAggregationJob(skillScoreSnapshotService, eventPublisher);
        when(skillScoreSnapshotService.refreshAllSnapshots())
                .thenReturn(new SkillScoreSnapshotService.SnapshotRefreshResult(2, List.of(1L, 2L)));

        job.aggregateSnapshots();

        verify(skillScoreSnapshotService).refreshAllSnapshots();
        verify(eventPublisher, org.mockito.Mockito.times(2))
                .publishEvent(org.mockito.ArgumentMatchers.any(SearchIndexSyncEvent.class));
    }
}
