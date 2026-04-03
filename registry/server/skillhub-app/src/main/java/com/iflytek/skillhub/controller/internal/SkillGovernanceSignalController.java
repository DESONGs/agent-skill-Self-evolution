package com.iflytek.skillhub.controller.internal;

import com.iflytek.skillhub.controller.BaseApiController;
import com.iflytek.skillhub.dto.ApiResponse;
import com.iflytek.skillhub.dto.ApiResponseFactory;
import com.iflytek.skillhub.dto.internal.SkillGovernanceSignalsResponse;
import com.iflytek.skillhub.service.SkillGovernanceSignalAppService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/internal/governance-signals")
public class SkillGovernanceSignalController extends BaseApiController {

    private final SkillGovernanceSignalAppService skillGovernanceSignalAppService;

    public SkillGovernanceSignalController(ApiResponseFactory responseFactory,
                                           SkillGovernanceSignalAppService skillGovernanceSignalAppService) {
        super(responseFactory);
        this.skillGovernanceSignalAppService = skillGovernanceSignalAppService;
    }

    @GetMapping("/skills")
    public ApiResponse<SkillGovernanceSignalsResponse> listSkillSignals(
            @RequestParam(required = false) Integer limit) {
        return ok("response.success.read", skillGovernanceSignalAppService.listSkillSignals(limit));
    }
}
