package com.iflytek.skillhub.job;

import com.iflytek.skillhub.search.SearchRebuildService;
import org.springframework.stereotype.Component;

@Component
public class SkillSearchProjectionRebuildJob {

    private final SearchRebuildService searchRebuildService;

    public SkillSearchProjectionRebuildJob(SearchRebuildService searchRebuildService) {
        this.searchRebuildService = searchRebuildService;
    }

    public void rebuildAll() {
        searchRebuildService.rebuildAll();
    }
}
