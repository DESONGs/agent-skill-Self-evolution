package com.iflytek.skillhub.controller.internal;

import com.iflytek.skillhub.controller.BaseApiController;
import com.iflytek.skillhub.dto.ApiResponse;
import com.iflytek.skillhub.dto.ApiResponseFactory;
import com.iflytek.skillhub.dto.internal.SkillFeedbackIngestionRequest;
import com.iflytek.skillhub.dto.internal.SkillFeedbackIngestionResponse;
import com.iflytek.skillhub.service.SkillFeedbackIngestionAppService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/internal/skill-feedback")
public class SkillFeedbackController extends BaseApiController {

    private final SkillFeedbackIngestionAppService skillFeedbackIngestionAppService;

    public SkillFeedbackController(ApiResponseFactory responseFactory,
                                   SkillFeedbackIngestionAppService skillFeedbackIngestionAppService) {
        super(responseFactory);
        this.skillFeedbackIngestionAppService = skillFeedbackIngestionAppService;
    }

    @PostMapping
    public ApiResponse<SkillFeedbackIngestionResponse> ingest(@RequestBody SkillFeedbackIngestionRequest request) {
        return ok("response.success.created", skillFeedbackIngestionAppService.ingest(request));
    }
}
