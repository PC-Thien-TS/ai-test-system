import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldAlert,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { loadQaCommandCenterArtifacts } from "@/lib/qa-command-center-loader";
import { CopyCommandButton } from "@/components/copy-command-button";
import { loadQaCommandCenterTrends, type TrendState } from "@/lib/qa-command-center-trends";
import { QaTrendChart } from "@/components/qa-trend-chart";
import { QaKpiCard } from "@/components/qa-kpi-card";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function statusBadgeClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes("block")) return "bg-red-100 text-red-800";
  if (normalized.includes("caution")) return "bg-amber-100 text-amber-800";
  if (normalized.includes("release")) return "bg-green-100 text-green-800";
  if (normalized.includes("active")) return "bg-red-100 text-red-800";
  if (normalized.includes("blocked")) return "bg-amber-100 text-amber-800";
  if (normalized.includes("suppressed")) return "bg-slate-100 text-slate-800";
  if (normalized.includes("green")) return "bg-green-100 text-green-800";
  if (normalized.includes("usable")) return "bg-blue-100 text-blue-800";
  return "bg-slate-100 text-slate-800";
}

function statusToneClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes("green") || normalized.includes("validated")) return "border-green-200 bg-green-50";
  if (normalized.includes("block") || normalized.includes("not_green")) return "border-red-200 bg-red-50";
  if (normalized.includes("partial") || normalized.includes("caution") || normalized.includes("regression")) return "border-amber-200 bg-amber-50";
  return "border-slate-200 bg-slate-50";
}

function severityBadgeClass(severity: string): string {
  const normalized = severity.toUpperCase();
  if (normalized === "P0") return "bg-red-100 text-red-800";
  if (normalized === "P1") return "bg-orange-100 text-orange-800";
  if (normalized === "P2") return "bg-amber-100 text-amber-800";
  if (normalized.includes("BLOCKER")) return "bg-purple-100 text-purple-800";
  return "bg-slate-100 text-slate-800";
}

function extractDecision(payload: Record<string, unknown>): string {
  return String(payload.decision ?? "unknown");
}

function extractScore(payload: Record<string, unknown>): number | string {
  return typeof payload.weighted_score === "number" ? payload.weighted_score : "N/A";
}

function extractConfidence(payload: Record<string, unknown>): string {
  return String(payload.confidence ?? "unknown");
}

function phaseLabel(phase: string): string {
  const labelMap: Record<string, string> = {
    auth: "Auth",
    order_core: "Order Core",
    search_store: "Search + Store",
    lifecycle: "Lifecycle",
    admin_consistency: "Admin Consistency",
    merchant_depth: "Merchant Depth",
    payment_realism: "Payment Realism",
  };
  return labelMap[phase] ?? phase;
}

function trendLabel(state: TrendState): string {
  if (state === "improving") return "improving";
  if (state === "worsening") return "worsening";
  if (state === "stable") return "stable";
  return "insufficient history";
}

function deltaText(label: string, delta: number | null): string {
  if (delta === null) return `${label}: N/A`;
  const sign = delta > 0 ? "+" : "";
  return `${label}: ${sign}${delta}`;
}

export default async function QaCommandCenterPage() {
  const bundle = await loadQaCommandCenterArtifacts();
  const releaseData = bundle.artifacts.releaseDecision.data ?? {};
  const snapshotData = bundle.artifacts.dashboardSnapshot.data ?? {};
  const clusterData = bundle.artifacts.defectCluster.data ?? {};
  const rerunData = bundle.artifacts.rerunPlan.data ?? {};
  const trendBundle = await loadQaCommandCenterTrends({
    releaseData,
    snapshotData,
    clusterData,
    rerunData,
  });

  const execSummary =
    (snapshotData.executive_summary as Record<string, unknown> | undefined) ?? {};
  const qualityHealth =
    (snapshotData.quality_health as Record<string, unknown> | undefined) ?? {};
  const defectFamilies =
    (snapshotData.active_defect_families as Array<Record<string, unknown>> | undefined)
    ?? (clusterData.defect_families as Array<Record<string, unknown>> | undefined)
    ?? [];
  const rerunOperations =
    (snapshotData.rerun_operations as Record<string, unknown> | undefined) ?? {};
  const healingActions =
    (snapshotData.healing_actions as Record<string, unknown> | undefined) ?? {};
  const releaseManagerView =
    (snapshotData.release_manager_view as Record<string, unknown> | undefined) ?? {};

  const decision = String(execSummary.decision ?? extractDecision(releaseData));
  const score = execSummary.weighted_score ?? extractScore(releaseData);
  const confidence = String(execSummary.confidence ?? extractConfidence(releaseData));
  const topReason = String(
    execSummary.top_reason_for_caution_or_block
      ?? (Array.isArray(releaseData.decision_reasoning) ? releaseData.decision_reasoning[0] : releaseData.summary)
      ?? "No decision reasoning available.",
  );
  const highestRiskFlow = String(execSummary.highest_risk_flow ?? "unknown");
  const shouldBlock = Boolean(releaseManagerView.should_release_be_blocked);
  const scoreDeltaObj =
    (snapshotData.evidence_delta_since_previous_snapshot as Record<string, unknown> | undefined)
    ?? (releaseData.evidence_delta_since_previous_snapshot as Record<string, unknown> | undefined)
    ?? {};
  const scoreDeltaData =
    (scoreDeltaObj.score_delta as Record<string, unknown> | undefined) ?? {};
  const scoreDelta = typeof scoreDeltaData.delta === "number" ? scoreDeltaData.delta : null;
  const previousScore = scoreDeltaData.previous_score;
  const currentScore = scoreDeltaData.current_score;
  const topRiskIcon = shouldBlock ? TriangleAlert : ShieldAlert;
  const TopRiskIcon = topRiskIcon;

  const targetSuites =
    (rerunOperations.target_suites as string[] | undefined)
    ?? (rerunData.target_suites as string[] | undefined)
    ?? [];
  const runnableCommands =
    (rerunOperations.runnable_commands as string[] | undefined)
    ?? (rerunData.powershell_commands as string[] | undefined)
    ?? [];
  const blockedReruns =
    (rerunOperations.blocked_reruns as Array<Record<string, unknown>> | undefined)
    ?? [];
  const rerunPriority = String(
    rerunOperations.priority
      ?? rerunData.priority
      ?? "unknown",
  );
  const suppressions =
    (rerunOperations.suppressions as string[] | undefined)
    ?? [];

  const actionsRun =
    (healingActions.actions_run as Array<Record<string, unknown>> | undefined)
    ?? (clusterData.healing_actions_run as Array<Record<string, unknown>> | undefined)
    ?? [];
  const actionsSkipped =
    (healingActions.actions_skipped as Array<Record<string, unknown>> | undefined)
    ?? (clusterData.healing_actions_skipped as Array<Record<string, unknown>> | undefined)
    ?? [];
  const effectSummary =
    (healingActions.effect_summary as Record<string, unknown> | undefined)
    ?? (clusterData.seed_state_delta as Record<string, unknown> | undefined)
    ?? {};

  const engineeringActions =
    (releaseManagerView.recommended_next_engineering_actions as string[] | undefined)
    ?? (releaseData.recommended_actions_before_release as string[] | undefined)
    ?? [];
  const qaActions =
    (releaseManagerView.recommended_next_qa_actions as string[] | undefined)
    ?? [];
  const watchItems =
    (releaseManagerView.top_post_release_watch_items as string[] | undefined)
    ?? [];
  const artifactGeneratedAt = String(
    execSummary.last_generated_timestamp_utc
      ?? releaseData.generated_at_utc
      ?? bundle.generatedAtUtc,
  );
  const newSeedsUnlocked =
    (healingActions.new_seeds_unlocked as string[] | undefined)
    ?? [];

  const phaseOrder = [
    "auth",
    "order_core",
    "search_store",
    "lifecycle",
    "admin_consistency",
    "merchant_depth",
    "payment_realism",
  ];

  const history = trendBundle.history;
  const hasTrendHistory = history.length >= 2;
  const scoreTrendData = history.map((entry) => ({
    timestamp: entry.timestamp,
    score: entry.score,
  }));
  const defectTrendData = history.map((entry) => ({
    timestamp: entry.timestamp,
    active_defects: entry.active_defect_count,
    product_defects: entry.product_defect_count,
    env_blockers: entry.env_blocker_count,
    coverage_gaps: entry.coverage_gap_count,
  }));
  const blockerTrendData = history.map((entry) => ({
    timestamp: entry.timestamp,
    unresolved_blockers: entry.unresolved_blocker_count,
  }));
  const healingTrendData = history.map((entry) => ({
    timestamp: entry.timestamp,
    healing_actions_run: entry.healing_actions_run_count,
  }));
  const scoreDeltaKpi = trendBundle.trendSummary.score_delta;
  const activeDefectDeltaKpi = trendBundle.trendSummary.defect_delta;
  const blockerDeltaKpi = trendBundle.trendSummary.blocker_delta;
  const healingDeltaKpi = trendBundle.trendSummary.healing_delta;

  return (
    <div className="space-y-6 p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">AI QA Command Center</h1>
          <p className="text-muted-foreground">
            Executive release-quality operations view backed by runtime artifacts.
          </p>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Clock3 className="h-3.5 w-3.5" />
              Last updated: {artifactGeneratedAt}
            </span>
            <span>Load timestamp: {bundle.generatedAtUtc}</span>
          </div>
        </div>
        <Link
          href={`/qa-command-center?refresh=${Date.now()}`}
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Release Decision</CardTitle>
          </CardHeader>
          <CardContent>
            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(decision)}`}>
              {decision}
            </span>
            <p className="mt-2 text-sm text-muted-foreground">{topReason}</p>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Weighted Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{String(score)}</p>
            <p className="text-sm text-muted-foreground">Confidence: {confidence}</p>
            {scoreDelta !== null ? (
              <p className={`mt-1 text-xs font-medium ${scoreDelta < 0 ? "text-red-700" : "text-green-700"}`}>
                Delta: {String(previousScore)} {"->"} {String(currentScore)} ({scoreDelta})
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Highest-risk Flow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <TopRiskIcon className="h-5 w-5 text-red-600" />
              <p className="text-sm font-semibold">{highestRiskFlow}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Release Manager Flag</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {shouldBlock ? (
                <>
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  <p className="text-sm font-semibold text-red-700">Release Block Recommended</p>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <p className="text-sm font-semibold text-green-700">No Hard Block Recommended</p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Trend Analytics v2</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <QaKpiCard
              title="Current Score"
              value={trendBundle.current.score ?? "N/A"}
              subtitle={`Decision: ${trendBundle.current.decision}`}
              deltaText={deltaText("Delta", scoreDeltaKpi)}
              trendState={trendBundle.trendSummary.score_state}
            />
            <QaKpiCard
              title="Active Defect Families"
              value={trendBundle.current.active_defect_count}
              subtitle="Product + env + coverage"
              deltaText={deltaText("Change", activeDefectDeltaKpi)}
              trendState={trendBundle.trendSummary.defect_state}
            />
            <QaKpiCard
              title="Unresolved Blockers"
              value={trendBundle.current.unresolved_blocker_count}
              subtitle="Env blockers + coverage gaps"
              deltaText={deltaText("Change", blockerDeltaKpi)}
              trendState={trendBundle.trendSummary.blocker_state}
            />
            <QaKpiCard
              title="Healing Actions Run"
              value={trendBundle.current.healing_actions_run_count}
              subtitle={`Rerun action: ${trendBundle.current.rerun_action}`}
              deltaText={deltaText("Change", healingDeltaKpi)}
              trendState={trendBundle.trendSummary.healing_state}
            />
            <QaKpiCard
              title="Rerun Readiness"
              value={trendLabel(trendBundle.trendSummary.rerun_readiness_state)}
              subtitle="Derived from rerun action movement"
            />
            <QaKpiCard
              title="History Snapshots"
              value={history.length}
              subtitle={trendBundle.historyBootstrapped ? "history bootstrapped" : "history loaded"}
              deltaText={trendBundle.historyUpdated ? "Current snapshot appended" : "No new snapshot appended"}
            />
          </div>

          {!hasTrendHistory ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              Insufficient trend history. At least 2 snapshots are needed to compute movement over time.
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <QaTrendChart
          title="Release Score Trend"
          description="Weighted score movement across snapshot history."
          data={scoreTrendData}
          lines={[
            { key: "score", label: "Score", color: "#2563eb" },
          ]}
          yDomain={[0, 100]}
        />
        <QaTrendChart
          title="Defect Family Trend"
          description="Active defects split by product/env/coverage groups."
          data={defectTrendData}
          lines={[
            { key: "active_defects", label: "Active Defects", color: "#dc2626" },
            { key: "product_defects", label: "Product Defects", color: "#ea580c" },
            { key: "env_blockers", label: "Env Blockers", color: "#7c3aed" },
            { key: "coverage_gaps", label: "Coverage Gaps", color: "#0284c7" },
          ]}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <QaTrendChart
          title="Blocker Burn-down"
          description="Unresolved blocker count over time."
          data={blockerTrendData}
          lines={[
            { key: "unresolved_blockers", label: "Unresolved Blockers", color: "#b91c1c" },
          ]}
        />
        <QaTrendChart
          title="Healing / Rerun Trend"
          description="Healing actions run per snapshot to track rerun readiness progression."
          data={healingTrendData}
          lines={[
            { key: "healing_actions_run", label: "Healing Actions Run", color: "#059669" },
          ]}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Risk Aging</CardTitle>
        </CardHeader>
        <CardContent>
          {trendBundle.riskAging.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No unresolved risk-aging data available yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-2">Family</th>
                    <th className="p-2">Title</th>
                    <th className="p-2">Days Open</th>
                    <th className="p-2">Snapshots Present</th>
                    <th className="p-2">Severity</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trendBundle.riskAging.map((item) => (
                    <tr key={item.family_id} className="border-b">
                      <td className="p-2 font-medium">{item.family_id}</td>
                      <td className="p-2">{item.title}</td>
                      <td className="p-2">{item.days_open}</td>
                      <td className="p-2">{item.snapshots_present}</td>
                      <td className="p-2">
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityBadgeClass(item.severity)}`}>
                          {item.severity}
                        </span>
                      </td>
                      <td className="p-2">{item.type}</td>
                      <td className="p-2">
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            History source: {trendBundle.historyFilePath}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Quality Health</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {phaseOrder.map((phase) => {
            const raw = qualityHealth[phase];
            const value = String(raw ?? "unknown");
            return (
              <div key={phase} className={`rounded-md border p-3 ${statusToneClass(value)}`}>
                <p className="text-xs uppercase text-muted-foreground">{phaseLabel(phase)}</p>
                <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(value)}`}>
                  {value}
                </span>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Defect Family Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          {defectFamilies.length === 0 ? (
            <p className="text-sm text-muted-foreground">No defect family data available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-2">Family</th>
                    <th className="p-2">Title</th>
                    <th className="p-2">Severity</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Impact</th>
                    <th className="p-2">Members</th>
                  </tr>
                </thead>
                <tbody>
                  {defectFamilies.map((family) => {
                    const familyId = String(family.family_id ?? "unknown");
                    const severity = String(family.suggested_severity ?? family.severity_suggestion ?? "unknown");
                    const status = String(family.status ?? "active");
                    const members = Array.isArray(family.member_cases) ? family.member_cases.join(", ") : "N/A";
                    return (
                      <tr key={familyId} className="border-b">
                        <td className="p-2 font-medium">{familyId}</td>
                        <td className="p-2 max-w-md">{String(family.title ?? "N/A")}</td>
                        <td className="p-2">
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityBadgeClass(severity)}`}>
                            {severity}
                          </span>
                        </td>
                        <td className="p-2">{String(family.type ?? "unknown")}</td>
                        <td className="p-2">
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusBadgeClass(status)}`}>
                            {status}
                          </span>
                        </td>
                        <td className="p-2">{String(family.release_impact ?? "unknown")}</td>
                        <td className="p-2 text-muted-foreground">{members}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Rerun Operations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs uppercase text-muted-foreground">Rerun action</p>
              <div className="mt-1 flex items-center gap-2">
                <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(String(rerunOperations.rerun_action ?? "unknown"))}`}>
                  {String(rerunOperations.rerun_action ?? "unknown")}
                </span>
                <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-800">
                  priority {rerunPriority}
                </span>
              </div>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Suppressions</p>
              <ul className="list-disc pl-5 text-sm">
                {suppressions.length > 0 ? suppressions.map((note) => <li key={note}>{note}</li>) : <li>None</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Target suites</p>
              <ul className="list-disc pl-5 text-sm">
                {targetSuites.length > 0 ? targetSuites.map((suite) => <li key={suite}>{suite}</li>) : <li>Data unavailable</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Runnable commands</p>
              <ul className="space-y-2 text-sm">
                {runnableCommands.length > 0 ? runnableCommands.map((cmd) => (
                  <li key={cmd} className="rounded-md border bg-slate-50 p-2">
                    <div className="flex items-start justify-between gap-2">
                      <code className="whitespace-pre-wrap break-all">{cmd}</code>
                      <CopyCommandButton value={cmd} />
                    </div>
                  </li>
                )) : <li>None</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Blocked reruns</p>
              <ul className="list-disc pl-5 text-sm">
                {blockedReruns.length > 0 ? blockedReruns.map((row) => (
                  <li key={String(row.suite)}>
                    <span className="font-medium">{String(row.suite ?? "unknown")}</span>: {String(row.blocker_reason ?? "blocked")}
                  </li>
                )) : <li>None</li>}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Healing Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs uppercase text-muted-foreground">Actions run</p>
              <ul className="list-disc pl-5 text-sm">
                {actionsRun.length > 0 ? actionsRun.map((item) => (
                  <li key={String(item.action_id)}>
                    {String(item.action_id)} ({String(item.status ?? "unknown")})
                  </li>
                )) : <li>None</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Actions skipped</p>
              <ul className="list-disc pl-5 text-sm">
                {actionsSkipped.length > 0 ? actionsSkipped.map((item) => (
                  <li key={String(item.action_id)}>
                    {String(item.action_id)}: {String(item.reason ?? "no reason")}
                  </li>
                )) : <li>None</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Newly unlocked seeds</p>
              <ul className="list-disc pl-5 text-sm">
                {newSeedsUnlocked.length > 0 ? newSeedsUnlocked.map((seed) => <li key={seed}>{seed}</li>) : <li>None</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Effect summary</p>
              <div className="space-y-1 rounded-md border bg-slate-50 p-3 text-xs text-slate-700">
                {Object.keys(effectSummary).length > 0 ? Object.entries(effectSummary).map(([k, v]) => (
                  <p key={k}>
                    <span className="font-semibold">{k}:</span>{" "}
                    <span>{Array.isArray(v) ? v.join(", ") : String(v)}</span>
                  </p>
                )) : <p>No effect summary available.</p>}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Release Manager View</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className={`rounded-md border p-3 ${shouldBlock ? "border-red-200 bg-red-50" : "border-green-200 bg-green-50"}`}>
            <p className="text-sm font-semibold">
              {shouldBlock ? "Release should be blocked" : "Release block not required"}
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-red-600" />
                <p className="text-sm font-semibold">Next Engineering Action</p>
              </div>
              <p className="text-sm">
                {engineeringActions[0] ?? "No engineering action available."}
              </p>
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-blue-600" />
                <p className="text-sm font-semibold">Next QA Action</p>
              </div>
              <p className="text-sm">
                {qaActions[0] ?? "No QA action available."}
              </p>
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs uppercase text-muted-foreground">Post-release watch items</p>
            <ul className="list-disc pl-5 text-sm">
              {watchItems.length > 0 ? watchItems.map((item) => <li key={item}>{item}</li>) : <li>None</li>}
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Artifact Availability</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {Object.values(bundle.artifacts).map((artifact) => (
            <div key={artifact.key} className="rounded-md border p-3">
              <p className="text-sm font-semibold">{artifact.fileName}</p>
              <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${artifact.available ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                {artifact.available ? "available" : "data unavailable"}
              </span>
              <p className="mt-2 text-xs text-muted-foreground">
                {artifact.resolvedPath ?? artifact.error ?? "No resolved path"}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
