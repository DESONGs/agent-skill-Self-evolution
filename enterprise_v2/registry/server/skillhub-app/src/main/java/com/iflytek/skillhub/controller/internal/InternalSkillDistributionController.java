package com.iflytek.skillhub.controller.internal;

import com.iflytek.skillhub.controller.BaseApiController;
import com.iflytek.skillhub.domain.namespace.NamespaceRole;
import com.iflytek.skillhub.dto.ApiResponse;
import com.iflytek.skillhub.dto.ApiResponseFactory;
import com.iflytek.skillhub.dto.internal.InternalSkillDistributionResponse;
import com.iflytek.skillhub.service.SkillDistributionAppService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/internal/skills")
public class InternalSkillDistributionController extends BaseApiController {

    private final SkillDistributionAppService skillDistributionAppService;

    public InternalSkillDistributionController(ApiResponseFactory responseFactory,
                                               SkillDistributionAppService skillDistributionAppService) {
        super(responseFactory);
        this.skillDistributionAppService = skillDistributionAppService;
    }

    @GetMapping("/{namespace}/{slug}/distribution")
    public ApiResponse<InternalSkillDistributionResponse> getLatestDistribution(
            @PathVariable String namespace,
            @PathVariable String slug,
            @RequestAttribute(value = "userId", required = false) String userId,
            @RequestAttribute(value = "userNsRoles", required = false) Map<Long, NamespaceRole> userNsRoles) {
        return ok(
                "response.success.read",
                skillDistributionAppService.getLatestInternalDistribution(
                        namespace,
                        slug,
                        userId,
                        userNsRoles != null ? userNsRoles : Map.of()
                )
        );
    }

    @GetMapping("/{namespace}/{slug}/versions/{version}/distribution")
    public ApiResponse<InternalSkillDistributionResponse> getVersionDistribution(
            @PathVariable String namespace,
            @PathVariable String slug,
            @PathVariable String version,
            @RequestAttribute(value = "userId", required = false) String userId,
            @RequestAttribute(value = "userNsRoles", required = false) Map<Long, NamespaceRole> userNsRoles) {
        return ok(
                "response.success.read",
                skillDistributionAppService.getVersionInternalDistribution(
                        namespace,
                        slug,
                        version,
                        userId,
                        userNsRoles != null ? userNsRoles : Map.of()
                )
        );
    }

    @GetMapping("/{namespace}/{slug}/tags/{tagName}/distribution")
    public ApiResponse<InternalSkillDistributionResponse> getTagDistribution(
            @PathVariable String namespace,
            @PathVariable String slug,
            @PathVariable String tagName,
            @RequestAttribute(value = "userId", required = false) String userId,
            @RequestAttribute(value = "userNsRoles", required = false) Map<Long, NamespaceRole> userNsRoles) {
        return ok(
                "response.success.read",
                skillDistributionAppService.getTagInternalDistribution(
                        namespace,
                        slug,
                        tagName,
                        userId,
                        userNsRoles != null ? userNsRoles : Map.of()
                )
        );
    }
}
