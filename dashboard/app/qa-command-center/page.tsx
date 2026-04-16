import Link from "next/link";
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldAlert, Wrench } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { loadQaCommandCenterArtifacts } from "@/lib/qa-command-center-loader";

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

export default async function QaCommandCenterPage() {
  const bundle = await loadQaCommandCenterArtifacts();
  const releaseData = bundle.artifacts.releaseDecision.data ?? {};
  const snapshotData = bundle.artifacts.dashboardSnapshot.data ?? {};
  const clusterData = bundle.artifacts.defectCluster.data ?? {};
  const rerunData = bundle.artifacts.rerunPlan.data ?? {};

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

  const phaseOrder = [
    "auth",
    "order_core",
    "search_store",
    "lifecycle",
    "admin_consistency",
    "merchant_depth",
    "payment_realism",
  ];

  return (
    <div className="space-y-6 p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">AI QA Command Center</h1>
          <p className="text-muted-foreground">
            Aggregated release, rerun, and self-healing intelligence snapshot.
          </p>
          <p className="text-xs text-muted-foreground">
            Generated at: {bundle.generatedAtUtc}
          </p>
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
        <Card>
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

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Weighted Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{String(score)}</p>
            <p className="text-sm text-muted-foreground">Confidence: {confidence}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Highest-risk Flow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-red-600" />
              <p className="text-sm font-semibold">{highestRiskFlow}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
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
          <CardTitle className="text-xl">Quality Health</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {phaseOrder.map((phase) => {
            const raw = qualityHealth[phase];
            const value = String(raw ?? "unknown");
            return (
              <div key={phase} className="rounded-md border p-3">
                <p className="text-xs uppercase text-muted-foreground">{phase}</p>
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
              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(String(rerunOperations.rerun_action ?? "unknown"))}`}>
                {String(rerunOperations.rerun_action ?? "unknown")}
              </span>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Target suites</p>
              <ul className="list-disc pl-5 text-sm">
                {targetSuites.length > 0 ? targetSuites.map((suite) => <li key={suite}>{suite}</li>) : <li>Data unavailable</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Runnable commands</p>
              <ul className="list-disc pl-5 text-sm">
                {runnableCommands.length > 0 ? runnableCommands.map((cmd) => <li key={cmd}><code>{cmd}</code></li>) : <li>None</li>}
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
              <p className="text-xs uppercase text-muted-foreground">Effect summary</p>
              <pre className="overflow-x-auto rounded-md bg-slate-50 p-3 text-xs text-slate-700">
                {JSON.stringify(effectSummary, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Release Manager View</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
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
