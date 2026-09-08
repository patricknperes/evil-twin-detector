import type {
  HistoryModelVersion,
  ModelArtifactStatusResponse
} from "../types/api";

export type ModelArtifactKey =
  | "reference"
  | "scaler"
  | "model"
  | "threshold";

export interface ModelArtifactView {
  key: ModelArtifactKey;
  title: string;
  role: string;
  path: string;
  available: boolean;
}

const metadata: Record<
  ModelArtifactKey,
  { title: string; role: string }
> = {
  reference: {
    title: "Referência normal",
    role: "Contexto congelado usado para derivar as features."
  },
  scaler: {
    title: "StandardScaler",
    role: "Transformação congelada aplicada antes da inferência."
  },
  model: {
    title: "One-Class SVM",
    role: "Modelo de detecção de anomalias do desktop_candidate_v1."
  },
  threshold: {
    title: "Threshold",
    role: "Limite congelado usado para converter score em decisão."
  }
};

export function artifactViews(
  status: ModelArtifactStatusResponse
): ModelArtifactView[] {
  const missing = new Set(
    status.missing_artifacts
  );

  const paths: Record<
    ModelArtifactKey,
    string
  > = {
    reference: status.reference_path,
    scaler: status.scaler_path,
    model: status.model_path,
    threshold: status.threshold_path
  };

  return (
    Object.keys(
      metadata
    ) as ModelArtifactKey[]
  ).map(
    key => ({
      key,
      title:
        metadata[key].title,
      role:
        metadata[key].role,
      path:
        paths[key],
      available:
        !missing.has(key)
    })
  );
}

export function activeModel(
  models: HistoryModelVersion[]
): HistoryModelVersion | null {
  return (
    models.find(
      model => model.active
    )
    ?? null
  );
}

export function shortFingerprint(
  value: string | null
): string {
  if (!value) {
    return "—";
  }

  if (value.length <= 25) {
    return value;
  }

  return `${value.slice(0, 12)}…${value.slice(-12)}`;
}
