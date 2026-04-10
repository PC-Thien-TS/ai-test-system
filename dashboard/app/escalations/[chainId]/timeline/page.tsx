"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, GitBranch, TrendingUp, CheckCircle, XCircle, Clock } from "lucide-react";
import Link from "next/link";

export default function EscalationTimelinePage() {
  const params = useParams();
  const chainId = params.chainId as string;

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", chainId],
    queryFn: () => api.getRun(chainId),
    enabled: !!chainId,
  });

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!run) {
    return <div className="flex h-screen items-center justify-center">Run not found</div>;
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center gap-4">
        <Link href={`/runs/${chainId}`}>
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Run
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Escalation Timeline</h1>
          <p className="text-muted-foreground">Chain {chainId.slice(0, 8)}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Escalation Chain Visualization
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 border rounded-lg">
              <div className="flex-1">
                <div className="font-medium">Original Run</div>
                <div className="text-sm text-muted-foreground">Path: {run.execution_path || "smoke"}</div>
                <div className="text-sm text-muted-foreground">Started: {new Date(run.started_at).toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-2">
                {run.status === "completed" && run.gate_result === "pass" && (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                )}
                {run.status === "completed" && run.gate_result === "fail" && (
                  <XCircle className="h-6 w-6 text-red-600" />
                )}
                {run.status === "failed" && <XCircle className="h-6 w-6 text-red-600" />}
                {run.status === "pending" && <Clock className="h-6 w-6 text-yellow-600" />}
              </div>
              <TrendingUp className="h-6 w-6 text-blue-600" />
            </div>

            {run.parent_run_id && (
              <div className="flex items-center gap-4 p-4 border rounded-lg bg-blue-50">
                <div className="flex-1">
                  <div className="font-medium">Escalated From</div>
                  <div className="text-sm text-muted-foreground">Parent: {run.parent_run_id.slice(0, 8)}</div>
                  <div className="text-sm text-muted-foreground">
                    Reason: {run.metadata?.escalation_reason || "Unknown"}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    From: {run.metadata?.escalation_from || "smoke"} → To: {run.metadata?.escalation_to || "standard"}
                  </div>
                </div>
                <TrendingUp className="h-6 w-6 text-blue-600" />
              </div>
            )}

            <div className="flex items-center gap-4 p-4 border rounded-lg">
              <div className="flex-1">
                <div className="font-medium">Current Run</div>
                <div className="text-sm text-muted-foreground">Path: {run.execution_path || "standard"}</div>
                <div className="text-sm text-muted-foreground">Started: {new Date(run.started_at).toLocaleString()}</div>
                {run.confidence_score && (
                  <div className="text-sm text-muted-foreground">
                    Confidence: {run.confidence_score.toFixed(2)}
                  </div>
                )}
                {run.fallback_ratio !== undefined && (
                  <div className="text-sm text-muted-foreground">
                    Fallback Ratio: {run.fallback_ratio.toFixed(2)}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {run.status === "completed" && run.gate_result === "pass" && (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                )}
                {run.status === "completed" && run.gate_result === "fail" && (
                  <XCircle className="h-6 w-6 text-red-600" />
                )}
                {run.status === "failed" && <XCircle className="h-6 w-6 text-red-600" />}
                {run.status === "pending" && <Clock className="h-6 w-6 text-yellow-600" />}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Escalation Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between p-2 border-b">
              <span className="font-medium">Escalation Depth</span>
              <span>1</span>
            </div>
            <div className="flex justify-between p-2 border-b">
              <span className="font-medium">Policy Applied</span>
              <span>{run.metadata?.escalation_policy ? "Yes" : "Default"}</span>
            </div>
            <div className="flex justify-between p-2 border-b">
              <span className="font-medium">Final Outcome</span>
              <span className="capitalize">{run.gate_result || "pending"}</span>
            </div>
            {run.metadata?.escalation_policy && (
              <div className="p-2 text-sm text-muted-foreground">
                <div>Fallback Threshold: {run.metadata.escalation_policy.fallback_threshold}</div>
                <div>Confidence Threshold: {run.metadata.escalation_policy.confidence_threshold}</div>
                <div>Max Depth: {run.metadata.escalation_policy.max_escalation_depth}</div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
