package com.iflytek.skillhub.dto.internal;

import java.util.List;

public record SkillGovernanceSignalsResponse(
        SkillGovernanceSignalSummaryResponse summary,
        List<SkillGovernanceSignalItemResponse> items
) {}
