import { readFile } from "node:fs/promises";
import path from "node:path";

type LoadState<T> = {
  key: string;
  fileName: string;
  resolvedPath: string | null;
  available: boolean;
  data: T | null;
  error: string | null;
};

type ArtifactMap = {
  releaseDecision: LoadState<Record<string, unknown>>;
  dashboardSnapshot: LoadState<Record<string, unknown>>;
  defectCluster: LoadState<Record<string, unknown>>;
  rerunPlan: LoadState<Record<string, unknown>>;
};

type CommandCenterArtifacts = {
  generatedAtUtc: string;
  artifacts: ArtifactMap;
};

const ARTIFACT_FILES = [
  { key: "releaseDecision", fileName: "release_decision.json" },
  { key: "dashboardSnapshot", fileName: "dashboard_snapshot.json" },
  { key: "defectCluster", fileName: "defect_cluster_report.json" },
  { key: "rerunPlan", fileName: "autonomous_rerun_plan.json" },
] as const;

function candidatePaths(fileName: string): string[] {
  const cwd = process.cwd();
  return [
    path.resolve(cwd, fileName),
    path.resolve(cwd, "..", fileName),
  ];
}

async function loadJsonArtifact(key: string, fileName: string): Promise<LoadState<Record<string, unknown>>> {
  const candidates = candidatePaths(fileName);
  let selectedPath: string | null = null;
  let rawContent: string | null = null;
  let lastError: string | null = null;

  for (const candidate of candidates) {
    try {
      rawContent = await readFile(candidate, "utf-8");
      selectedPath = candidate;
      break;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
  }

  if (!selectedPath || rawContent === null) {
    return {
      key,
      fileName,
      resolvedPath: null,
      available: false,
      data: null,
      error: lastError ?? "Artifact file not found.",
    };
  }

  try {
    const parsed = JSON.parse(rawContent) as Record<string, unknown>;
    return {
      key,
      fileName,
      resolvedPath: selectedPath,
      available: true,
      data: parsed,
      error: null,
    };
  } catch (error) {
    return {
      key,
      fileName,
      resolvedPath: selectedPath,
      available: false,
      data: null,
      error: error instanceof Error ? error.message : "Invalid JSON content.",
    };
  }
}

export async function loadQaCommandCenterArtifacts(): Promise<CommandCenterArtifacts> {
  const loaded = await Promise.all(
    ARTIFACT_FILES.map((artifact) => loadJsonArtifact(artifact.key, artifact.fileName)),
  );

  const artifacts = {
    releaseDecision: loaded.find((item) => item.key === "releaseDecision")!,
    dashboardSnapshot: loaded.find((item) => item.key === "dashboardSnapshot")!,
    defectCluster: loaded.find((item) => item.key === "defectCluster")!,
    rerunPlan: loaded.find((item) => item.key === "rerunPlan")!,
  };

  return {
    generatedAtUtc: new Date().toISOString(),
    artifacts,
  };
}

export type { CommandCenterArtifacts, LoadState };
