package com.iflytek.skillhub.controller.internal;

import com.iflytek.skillhub.auth.rbac.PlatformPrincipal;
import com.iflytek.skillhub.controller.BaseApiController;
import com.iflytek.skillhub.dto.ApiResponse;
import com.iflytek.skillhub.dto.ApiResponseFactory;
import com.iflytek.skillhub.dto.internal.SkillCandidateCreateRequest;
import com.iflytek.skillhub.dto.internal.SkillCandidateDetailResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidatePublishRequest;
import com.iflytek.skillhub.dto.internal.SkillCandidatePublishResponse;
import com.iflytek.skillhub.dto.internal.SkillCandidateSummaryResponse;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionCreateRequest;
import com.iflytek.skillhub.dto.internal.SkillPromotionDecisionResponse;
import com.iflytek.skillhub.service.SkillCandidateAppService;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/internal/candidates")
public class SkillCandidateController extends BaseApiController {

    private final SkillCandidateAppService skillCandidateAppService;

    public SkillCandidateController(ApiResponseFactory responseFactory,
                                    SkillCandidateAppService skillCandidateAppService) {
        super(responseFactory);
        this.skillCandidateAppService = skillCandidateAppService;
    }

    @PostMapping
    public ApiResponse<SkillCandidateDetailResponse> createCandidate(
            @RequestBody SkillCandidateCreateRequest request,
            @RequestAttribute(value = "userId", required = false) String userId) {
        return ok("response.success.created", skillCandidateAppService.create(request, userId));
    }

    @GetMapping
    public ApiResponse<List<SkillCandidateSummaryResponse>> listCandidates(
            @RequestParam(required = false) String promotionState) {
        return ok("response.success.read", skillCandidateAppService.list(promotionState));
    }

    @GetMapping("/{candidateId}")
    public ApiResponse<SkillCandidateDetailResponse> getCandidate(@PathVariable Long candidateId) {
        return ok("response.success.read", skillCandidateAppService.get(candidateId));
    }

    @PutMapping("/{candidateId}")
    public ApiResponse<SkillCandidateDetailResponse> updateCandidate(
            @PathVariable Long candidateId,
            @RequestBody SkillCandidateCreateRequest request,
            @RequestAttribute(value = "userId", required = false) String userId) {
        return ok("response.success.updated", skillCandidateAppService.update(candidateId, request, userId));
    }

    @DeleteMapping("/{candidateId}")
    public ApiResponse<SkillCandidateDetailResponse> archiveCandidate(@PathVariable Long candidateId) {
        return ok("response.success.deleted", skillCandidateAppService.archive(candidateId));
    }

    @PostMapping("/{candidateId}/promotion-decisions")
    public ApiResponse<SkillPromotionDecisionResponse> appendDecision(
            @PathVariable Long candidateId,
            @RequestBody SkillPromotionDecisionCreateRequest request,
            @RequestAttribute(value = "userId", required = false) String userId) {
        return ok("response.success.created", skillCandidateAppService.createDecision(candidateId, request, userId));
    }

    @PostMapping("/{candidateId}/publish")
    public ApiResponse<SkillCandidatePublishResponse> publishCandidate(
            @PathVariable Long candidateId,
            @RequestBody SkillCandidatePublishRequest request,
            @AuthenticationPrincipal PlatformPrincipal principal) {
        return ok("response.success.created", skillCandidateAppService.publish(candidateId, request, principal));
    }
}
