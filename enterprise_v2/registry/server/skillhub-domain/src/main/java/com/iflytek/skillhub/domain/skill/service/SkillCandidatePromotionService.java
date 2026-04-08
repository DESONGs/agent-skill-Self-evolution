package com.iflytek.skillhub.domain.skill.service;

import com.iflytek.skillhub.domain.candidate.SkillCandidate;
import com.iflytek.skillhub.domain.candidate.SkillCandidateRepository;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecision;
import com.iflytek.skillhub.domain.candidate.SkillPromotionDecisionRepository;
import com.iflytek.skillhub.domain.feedback.SkillScoreSnapshotService;
import com.iflytek.skillhub.domain.shared.exception.DomainBadRequestException;
import com.iflytek.skillhub.domain.skill.SkillVersion;
import com.iflytek.skillhub.domain.skill.SkillVisibility;
import com.iflytek.skillhub.domain.skill.validation.PackageEntry;
import com.iflytek.skillhub.domain.skill.validation.SkillPackagePolicy;
import com.iflytek.skillhub.storage.ObjectStorageService;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SkillCandidatePromotionService {

    public record CandidatePublishResult(
            SkillCandidate candidate,
            Long skillId,
            String slug,
            SkillVersion version
    ) {
    }

    private final SkillCandidateRepository skillCandidateRepository;
    private final SkillPromotionDecisionRepository skillPromotionDecisionRepository;
    private final ObjectStorageService objectStorageService;
    private final SkillPublishService skillPublishService;
    private final SkillScoreSnapshotService skillScoreSnapshotService;

    public SkillCandidatePromotionService(SkillCandidateRepository skillCandidateRepository,
                                          SkillPromotionDecisionRepository skillPromotionDecisionRepository,
                                          ObjectStorageService objectStorageService,
                                          SkillPublishService skillPublishService,
                                          SkillScoreSnapshotService skillScoreSnapshotService) {
        this.skillCandidateRepository = skillCandidateRepository;
        this.skillPromotionDecisionRepository = skillPromotionDecisionRepository;
        this.objectStorageService = objectStorageService;
        this.skillPublishService = skillPublishService;
        this.skillScoreSnapshotService = skillScoreSnapshotService;
    }

    @Transactional
    public CandidatePublishResult publish(Long candidateId,
                                          String namespace,
                                          SkillVisibility visibility,
                                          String publisherId,
                                          Set<String> platformRoles) {
        SkillCandidate candidate = skillCandidateRepository.findById(candidateId)
                .orElseThrow(() -> new DomainBadRequestException("candidate.not_found", candidateId));
        assertCandidatePublishable(candidate);

        List<PackageEntry> entries = loadEntries(candidate.getGeneratedBundleKey());
        SkillPublishService.PublishResult publishResult = skillPublishService.publishFromEntries(
                namespace,
                entries,
                publisherId,
                visibility,
                platformRoles
        );

        candidate.setPublishedSkillId(publishResult.skillId());
        candidate.setPublishedVersionId(publishResult.version().getId());
        candidate.setPromotionState("PUBLISHED");
        SkillCandidate saved = skillCandidateRepository.save(candidate);
        skillScoreSnapshotService.refreshSkillSnapshot(publishResult.skillId());
        return new CandidatePublishResult(saved, publishResult.skillId(), publishResult.slug(), publishResult.version());
    }

    private void assertCandidatePublishable(SkillCandidate candidate) {
        if (candidate.getGeneratedBundleKey() == null || candidate.getGeneratedBundleKey().isBlank()) {
            throw new DomainBadRequestException("candidate.bundle.required", candidate.getId());
        }
        List<SkillPromotionDecision> decisions =
                skillPromotionDecisionRepository.findBySkillCandidateIdOrderByDecidedAtDesc(candidate.getId());
        boolean hasPromoteDecision = decisions.stream().findFirst()
                .map(SkillPromotionDecision::getDecision)
                .filter("PROMOTE"::equalsIgnoreCase)
                .isPresent();
        boolean promotableState = "PROMOTION_PENDING".equalsIgnoreCase(candidate.getPromotionState())
                || "GATE_PASSED".equalsIgnoreCase(candidate.getPromotionState())
                || "PUBLISHED".equalsIgnoreCase(candidate.getPromotionState());
        if (!hasPromoteDecision && !promotableState) {
            throw new DomainBadRequestException("candidate.not_ready_for_publish", candidate.getId());
        }
    }

    private List<PackageEntry> loadEntries(String bundleKey) {
        try (InputStream inputStream = objectStorageService.getObject(bundleKey);
             ZipInputStream zipInputStream = new ZipInputStream(inputStream)) {
            List<PackageEntry> entries = new ArrayList<>();
            ZipEntry zipEntry;
            while ((zipEntry = zipInputStream.getNextEntry()) != null) {
                if (zipEntry.isDirectory()) {
                    zipInputStream.closeEntry();
                    continue;
                }
                String normalizedPath = SkillPackagePolicy.normalizeEntryPath(zipEntry.getName());
                byte[] content = readEntry(zipInputStream, normalizedPath);
                entries.add(new PackageEntry(
                        normalizedPath,
                        content,
                        content.length,
                        determineContentType(normalizedPath)
                ));
                zipInputStream.closeEntry();
            }
            return stripSingleRootDirectory(entries);
        } catch (IOException ex) {
            throw new IllegalStateException("Failed to read candidate bundle: " + bundleKey, ex);
        }
    }

    private byte[] readEntry(ZipInputStream zipInputStream, String path) throws IOException {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = zipInputStream.read(buffer)) != -1) {
            outputStream.write(buffer, 0, read);
        }
        return outputStream.toByteArray();
    }

    private List<PackageEntry> stripSingleRootDirectory(List<PackageEntry> entries) {
        if (entries.isEmpty()) {
            return entries;
        }
        Set<String> rootSegments = new HashSet<>();
        for (PackageEntry entry : entries) {
            int slashIndex = entry.path().indexOf('/');
            if (slashIndex < 0) {
                return entries;
            }
            rootSegments.add(entry.path().substring(0, slashIndex));
        }
        if (rootSegments.size() != 1) {
            return entries;
        }
        String prefix = rootSegments.iterator().next() + "/";
        return entries.stream()
                .map(entry -> new PackageEntry(
                        entry.path().substring(prefix.length()),
                        entry.content(),
                        entry.size(),
                        entry.contentType()))
                .toList();
    }

    private String determineContentType(String filename) {
        String lower = filename.toLowerCase();
        if (lower.endsWith(".py")) return "text/x-python";
        if (lower.endsWith(".json")) return "application/json";
        if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "application/x-yaml";
        if (lower.endsWith(".txt")) return "text/plain";
        if (lower.endsWith(".md")) return "text/markdown";
        if (lower.endsWith(".html")) return "text/html";
        if (lower.endsWith(".css")) return "text/css";
        if (lower.endsWith(".csv")) return "text/csv";
        if (lower.endsWith(".xml")) return "application/xml";
        if (lower.endsWith(".js")) return "text/javascript";
        if (lower.endsWith(".ts")) return "text/typescript";
        if (lower.endsWith(".sh") || lower.endsWith(".bash") || lower.endsWith(".zsh")) return "text/x-shellscript";
        return "application/octet-stream";
    }
}
