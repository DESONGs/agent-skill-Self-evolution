package com.iflytek.skillhub.search.event;

public record SearchIndexSyncEvent(Long skillId, SearchIndexAction action) {}
