import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

type AnyRecord = Record<string, unknown>;

type TrendState = "improving" | "stable" | "worsening" | "insufficient_history";

type TrendSnapshotEntry = {
  timestamp: string;
  decision: string;
  score: number | null;
  confidence: string;
  top_risk: string;
  active_defect_count: number;
  product_defect_count: number;
  env_blocker_count: number;
  coverage_gap_count: number;
  rerun_action: string;
  healing_actions_run_count: number;
  unresolved_blocker_count: number;
  active_defect_family_ids: string[];
};

type RiskAgingItem = {
  family_id: string;
  title: string;
  type: string;
  status: string;
  severity: string;
  release_impact: string;
  days_open: number;
  snapshots_present: number;
};

type QaCommandCenterTrendBundle = {
  historyFilePath: string;
  history: TrendSnapshotEntry[];
  current: TrendSnapshotEntry;
  previous: TrendSnapshotEntry | null;
  historyBootstrapped: boolean;
  historyUpdated: boolean;
  trendSummary: {
    score_delta: number | null;
    score_state: TrendState;
    defect_delta: number | null;
    defect_state: TrendState;
    blocker_delta: number | null;
    blocker_state: TrendState;
    healing_delta: number | null;
    healing_state: TrendState;
    rerun_readiness_state: TrendState;
  };
  riskAging: RiskAgingItem[];
};

type TrendInput = {
  releaseData: AnyRecord;
  snapshotData: AnyRecord;
  clusterData: AnyRecord;
  rerunData: AnyRecord;
};

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" ? (value as AnyRecord) : {};
}

function asRecordArray(value: unknown): AnyRecord[] {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as AnyRecord[] : [];
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function numericOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function nowUtcIso(): string {
  return new Date().toISOString();
}

function selectFamilySet(snapshotData: AnyRecord, clusterData: AnyRecord): AnyRecord[] {
  const fromSnapshot = asRecordArray(snapshotData.active_defect_families);
  if (fromSnapshot.length > 0) {
    return fromSnapshot;
  }
  return asRecordArray(clusterData.defect_families);
}

function selectTimestamp(snapshotData: AnyRecord, releaseData: AnyRecord): string {
  const execSummary = asRecord(snapshotData.executive_summary);
  const snapshotTs = execSummary.last_generated_timestamp_utc;
  if (typeof snapshotTs === "string" && snapshotTs.trim().length > 0) {
    return snapshotTs;
  }
  const releaseTs = releaseData.generated_at_utc;
  if (typeof releaseTs === "string" && releaseTs.trim().length > 0) {
    return releaseTs;
  }
  return nowUtcIso();
}

function readDecision(snapshotData: AnyRecord, releaseData: AnyRecord): string {
  const execSummary = asRecord(snapshotData.executive_summary);
  return String(execSummary.decision ?? releaseData.decision ?? "unknown");
}

function readScore(snapshotData: AnyRecord, releaseData: AnyRecord): number | null {
  const execSummary = asRecord(snapshotData.executive_summary);
  const score = execSummary.weighted_score ?? releaseData.weighted_score;
  return numericOrNull(score);
}

function readConfidence(snapshotData: AnyRecord, releaseData: AnyRecord): string {
  const execSummary = asRecord(snapshotData.executive_summary);
  return String(execSummary.confidence ?? releaseData.confidence ?? "unknown");
}

function readTopRisk(snapshotData: AnyRecord): string {
  const execSummary = asRecord(snapshotData.executive_summary);
  return String(execSummary.highest_risk_flow ?? "unknown");
}

function readRerunAction(snapshotData: AnyRecord, rerunData: AnyRecord): string {
  const rerunOps = asRecord(snapshotData.rerun_operations);
  return String(rerunOps.rerun_action ?? rerunData.rerun_action ?? "unknown");
}

function readHealingRunCount(snapshotData: AnyRecord, clusterData: AnyRecord): number {
  const healing = asRecord(snapshotData.healing_actions);
  const actionsRun = asRecordArray(healing.actions_run);
  if (actionsRun.length > 0) {
    return actionsRun.length;
  }
  return asRecordArray(clusterData.healing_actions_run).length;
}

function buildEntry(input: TrendInput): TrendSnapshotEntry {
  const families = selectFamilySet(input.snapshotData, input.clusterData);
  const productDefectCount = families.filter((item) => String(item.type ?? "").toLowerCase() === "product_defect").length;
  const envBlockerCount = families.filter((item) => String(item.type ?? "").toLowerCase() === "env_blocker").length;
  const coverageGapCount = families.filter((item) => String(item.type ?? "").toLowerCase() === "coverage_gap").length;

  return {
    timestamp: selectTimestamp(input.snapshotData, input.releaseData),
    decision: readDecision(input.snapshotData, input.releaseData),
    score: readScore(input.snapshotData, input.releaseData),
    confidence: readConfidence(input.snapshotData, input.releaseData),
    top_risk: readTopRisk(input.snapshotData),
    active_defect_count: families.length,
    product_defect_count: productDefectCount,
    env_blocker_count: envBlockerCount,
    coverage_gap_count: coverageGapCount,
    rerun_action: readRerunAction(input.snapshotData, input.rerunData),
    healing_actions_run_count: readHealingRunCount(input.snapshotData, input.clusterData),
    unresolved_blocker_count: envBlockerCount + coverageGapCount,
    active_defect_family_ids: families.map((item) => String(item.family_id ?? "unknown")),
  };
}

function candidateHistoryPaths(fileName: string): string[] {
  const cwd = process.cwd();
  return [
    path.resolve(cwd, fileName),
    path.resolve(cwd, "..", fileName),
  ];
}

async function resolveHistoryPath(fileName: string): Promise<string> {
  const candidates = candidateHistoryPaths(fileName);
  for (const candidate of candidates) {
    try {
      await readFile(candidate, "utf-8");
      return candidate;
    } catch {
      // keep scanning
    }
  }
  // Default to repository root when running from dashboard.
  return candidates[candidates.length - 1];
}

function normalizeEntry(raw: AnyRecord): TrendSnapshotEntry | null {
  const timestamp = typeof raw.timestamp === "string" && raw.timestamp.length > 0 ? raw.timestamp : null;
  if (!timestamp) {
    return null;
  }
  return {
    timestamp,
    decision: String(raw.decision ?? "unknown"),
    score: numericOrNull(raw.score),
    confidence: String(raw.confidence ?? "unknown"),
    top_risk: String(raw.top_risk ?? "unknown"),
    active_defect_count: typeof raw.active_defect_count === "number" ? raw.active_defect_count : 0,
    product_defect_count: typeof raw.product_defect_count === "number" ? raw.product_defect_count : 0,
    env_blocker_count: typeof raw.env_blocker_count === "number" ? raw.env_blocker_count : 0,
    coverage_gap_count: typeof raw.coverage_gap_count === "number" ? raw.coverage_gap_count : 0,
    rerun_action: String(raw.rerun_action ?? "unknown"),
    healing_actions_run_count: typeof raw.healing_actions_run_count === "number" ? raw.healing_actions_run_count : 0,
    unresolved_blocker_count: typeof raw.unresolved_blocker_count === "number" ? raw.unresolved_blocker_count : 0,
    active_defect_family_ids: asStringArray(raw.active_defect_family_ids),
  };
}

async function loadHistory(historyPath: string): Promise<{ entries: TrendSnapshotEntry[]; bootstrapped: boolean }> {
  try {
    const raw = await readFile(historyPath, "utf-8");
    const parsed = JSON.parse(raw);
    const entries = Array.isArray(parsed)
      ? parsed.map((item) => normalizeEntry(asRecord(item))).filter((item): item is TrendSnapshotEntry => item !== null)
      : [];
    return { entries, bootstrapped: false };
  } catch {
    return { entries: [], bootstrapped: true };
  }
}

function toFingerprint(entry: TrendSnapshotEntry): string {
  const familyIds = [...entry.active_defect_family_ids].sort().join(",");
  return [
    entry.decision,
    entry.score ?? "null",
    entry.confidence,
    entry.top_risk,
    entry.active_defect_count,
    entry.product_defect_count,
    entry.env_blocker_count,
    entry.coverage_gap_count,
    entry.rerun_action,
    entry.healing_actions_run_count,
    entry.unresolved_blocker_count,
    familyIds,
  ].join("|");
}

function shouldAppend(last: TrendSnapshotEntry | null, current: TrendSnapshotEntry): boolean {
  if (!last) {
    return true;
  }
  if (last.timestamp === current.timestamp) {
    return false;
  }
  return toFingerprint(last) !== toFingerprint(current);
}

function sortHistory(entries: TrendSnapshotEntry[]): TrendSnapshotEntry[] {
  return [...entries].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
}

async function persistHistory(historyPath: string, history: TrendSnapshotEntry[]): Promise<void> {
  const serialized = `${JSON.stringify(history, null, 2)}\n`;
  await writeFile(historyPath, serialized, "utf-8");
}

function scoreTrend(delta: number | null): TrendState {
  if (delta === null) {
    return "insufficient_history";
  }
  if (delta > 0) {
    return "improving";
  }
  if (delta < 0) {
    return "worsening";
  }
  return "stable";
}

function inverseTrend(delta: number | null): TrendState {
  if (delta === null) {
    return "insufficient_history";
  }
  if (delta < 0) {
    return "improving";
  }
  if (delta > 0) {
    return "worsening";
  }
  return "stable";
}

function rerunReadinessRank(action: string): number {
  const normalized = action.toLowerCase();
  if (normalized === "no_rerun_needed") return 4;
  if (normalized === "targeted_rerun") return 3;
  if (normalized === "phased_rerun") return 2;
  if (normalized === "block_rerun_env") return 1;
  if (normalized === "escalate_product_risk") return 0;
  return 1;
}

function rerunReadinessTrend(previousAction: string | null, currentAction: string): TrendState {
  if (!previousAction) {
    return "insufficient_history";
  }
  const delta = rerunReadinessRank(currentAction) - rerunReadinessRank(previousAction);
  if (delta > 0) return "improving";
  if (delta < 0) return "worsening";
  return "stable";
}

function computeRiskAging(history: TrendSnapshotEntry[], latestFamilies: AnyRecord[]): RiskAgingItem[] {
  if (history.length === 0 || latestFamilies.length === 0) {
    return [];
  }

  const now = new Date(history[history.length - 1].timestamp).getTime();
  const items: RiskAgingItem[] = [];

  for (const family of latestFamilies) {
    const familyId = String(family.family_id ?? "unknown");
    const status = String(family.status ?? "active");
    const loweredStatus = status.toLowerCase();
    if (loweredStatus === "suppressed" || loweredStatus === "resolved") {
      continue;
    }

    const snapshotsWithFamily = history.filter((entry) => entry.active_defect_family_ids.includes(familyId));
    if (snapshotsWithFamily.length === 0) {
      continue;
    }

    const firstSeen = new Date(snapshotsWithFamily[0].timestamp).getTime();
    const daysOpen = Math.max(0, Math.floor((now - firstSeen) / (1000 * 60 * 60 * 24)));

    items.push({
      family_id: familyId,
      title: String(family.title ?? "N/A"),
      type: String(family.type ?? "unknown"),
      status,
      severity: String(family.suggested_severity ?? family.severity_suggestion ?? "unknown"),
      release_impact: String(family.release_impact ?? "unknown"),
      days_open: daysOpen,
      snapshots_present: snapshotsWithFamily.length,
    });
  }

  return items.sort((a, b) => {
    if (b.days_open !== a.days_open) {
      return b.days_open - a.days_open;
    }
    return b.snapshots_present - a.snapshots_present;
  });
}

export async function loadQaCommandCenterTrends(input: TrendInput): Promise<QaCommandCenterTrendBundle> {
  const historyPath = await resolveHistoryPath("qa_snapshot_history.json");
  const { entries: rawHistory, bootstrapped } = await loadHistory(historyPath);
  const current = buildEntry(input);
  const sortedHistory = sortHistory(rawHistory);
  const last = sortedHistory.length > 0 ? sortedHistory[sortedHistory.length - 1] : null;

  let historyUpdated = false;
  const updatedHistory = [...sortedHistory];
  if (shouldAppend(last, current)) {
    updatedHistory.push(current);
    historyUpdated = true;
  }

  const finalHistory = sortHistory(updatedHistory);
  if (bootstrapped || historyUpdated) {
    await persistHistory(historyPath, finalHistory);
  }

  const previous = finalHistory.length >= 2 ? finalHistory[finalHistory.length - 2] : null;
  const latest = finalHistory[finalHistory.length - 1] ?? current;

  const scoreDelta =
    previous && latest.score !== null && previous.score !== null
      ? latest.score - previous.score
      : null;

  const defectDelta = previous
    ? latest.active_defect_count - previous.active_defect_count
    : null;

  const blockerDelta = previous
    ? latest.unresolved_blocker_count - previous.unresolved_blocker_count
    : null;

  const healingDelta = previous
    ? latest.healing_actions_run_count - previous.healing_actions_run_count
    : null;

  const latestFamilies = selectFamilySet(input.snapshotData, input.clusterData);

  return {
    historyFilePath: historyPath,
    history: finalHistory,
    current: latest,
    previous,
    historyBootstrapped: bootstrapped,
    historyUpdated,
    trendSummary: {
      score_delta: scoreDelta,
      score_state: scoreTrend(scoreDelta),
      defect_delta: defectDelta,
      defect_state: inverseTrend(defectDelta),
      blocker_delta: blockerDelta,
      blocker_state: inverseTrend(blockerDelta),
      healing_delta: healingDelta,
      healing_state: scoreTrend(healingDelta),
      rerun_readiness_state: rerunReadinessTrend(previous?.rerun_action ?? null, latest.rerun_action),
    },
    riskAging: computeRiskAging(finalHistory, latestFamilies),
  };
}

export type {
  QaCommandCenterTrendBundle,
  RiskAgingItem,
  TrendSnapshotEntry,
  TrendState,
};
