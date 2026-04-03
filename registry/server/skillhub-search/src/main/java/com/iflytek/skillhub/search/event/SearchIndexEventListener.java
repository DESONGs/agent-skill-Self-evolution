package com.iflytek.skillhub.search.event;

import com.iflytek.skillhub.domain.event.SkillPublishedEvent;
import com.iflytek.skillhub.domain.event.SkillStatusChangedEvent;
import com.iflytek.skillhub.domain.skill.SkillStatus;
import com.iflytek.skillhub.search.SearchIndexService;
import com.iflytek.skillhub.search.SearchRebuildService;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * Reacts to committed skill lifecycle events and keeps the search index synchronized.
 */
@Component
public class SearchIndexEventListener {

    private final SearchRebuildService searchRebuildService;
    private final SearchIndexService searchIndexService;

    public SearchIndexEventListener(
            SearchRebuildService searchRebuildService,
            SearchIndexService searchIndexService) {
        this.searchRebuildService = searchRebuildService;
        this.searchIndexService = searchIndexService;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    @Async("skillhubEventExecutor")
    public void onSkillPublished(SkillPublishedEvent event) {
        dispatch(new SearchIndexSyncEvent(event.skillId(), SearchIndexAction.REBUILD));
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    @Async("skillhubEventExecutor")
    public void onSkillStatusChanged(SkillStatusChangedEvent event) {
        SearchIndexAction action =
                event.newStatus() == SkillStatus.ARCHIVED
                        ? SearchIndexAction.REMOVE
                        : SearchIndexAction.REBUILD;
        dispatch(new SearchIndexSyncEvent(event.skillId(), action));
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    @Async("skillhubEventExecutor")
    public void onSearchIndexSyncEvent(SearchIndexSyncEvent event) {
        dispatch(event);
    }

    private void dispatch(SearchIndexSyncEvent event) {
        if (event.action() == SearchIndexAction.REMOVE) {
            searchIndexService.remove(event.skillId());
        } else {
            searchRebuildService.rebuildBySkill(event.skillId());
        }
    }
}
