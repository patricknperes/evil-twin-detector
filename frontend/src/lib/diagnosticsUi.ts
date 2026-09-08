import type { DiagnosticsSupportBundleResponse } from "../types/api";

export function supportBundleFileName(generatedAtUtc: string): string {
  const timestamp = generatedAtUtc.replace(/[:.]/g, "-").replace("Z", "");
  return `evil-twin-diagnostics-${timestamp}.json`;
}

export function supportBundleJson(bundle: DiagnosticsSupportBundleResponse): string {
  return JSON.stringify(bundle, null, 2);
}

export function availableArtifactCount(bundle: DiagnosticsSupportBundleResponse): number {
  return Object.values(bundle.model.artifact_available).filter(Boolean).length;
}
