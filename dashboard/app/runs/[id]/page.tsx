"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Clock, CheckCircle, XCircle, AlertTriangle, Play, RefreshCw } from "lucide-react";
import Link from "next/link";
import { ConfidenceTrendChart } from "@/components/confidence-trend-chart";
import { ExecutionDepthChart } from "@/components/execution-depth-chart";
import { FallbackRatioHeatmap } from "@/components/fallback-ratio-heatmap";
import { PluginMaturityHeatmap } from "@/components/plugin-maturity-heatmap";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [liveData, setLiveData] = useState<any>(null);
  const [isLive, setIsLive] = useState(false);

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    enabled: !!runId,
  });

  // SSE for live updates
  useEffect(() => {
    if (!runId) return;

    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/runs/${runId}/updates`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLiveData(data);
      setIsLive(true);
    };

    eventSource.onerror = () => {
      setIsLive(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);

  if (runLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!run) {
    return <div className="flex h-screen items-center justify-center">Run not found</div>;
  }

  const displayData = liveData || run;
  const confidenceScore = displayData?.confidence_score || 0;
  const fallbackRatio = displayData?.fallback_ratio || 0;
  const realExecutionRatio = displayData?.real_execution_ratio || 0;

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/runs">
            <Button variant="outline" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Runs
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Run {runId.slice(0, 8)}</h1>
            <p className="text-muted-foreground">
              {new Date(run.started_at).toLocaleString()}
              {isLive && (
                <span className="ml-2 inline-flex items-center text-green-600">
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  Live
                </span>
              )}
            </p>
          </div>
        </div>
        <Button size="sm">
          <Play className="mr-2 h-4 w-4" />
          Rerun
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{run.status}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(confidenceScore * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Fallback Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(fallbackRatio * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Real Execution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(realExecutionRatio * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <ConfidenceTrendChart
          data={[
            {
              timestamp: run.started_at,
              confidence_score: confidenceScore,
            },
          ]}
        />
        <ExecutionDepthChart
          data={[
            { name: "Current Run", execution_depth_score: 0.75 },
          ]}
        />
        <FallbackRatioHeatmap
          data={[
            { name: "Current Run", fallback_ratio: fallbackRatio, real_execution_ratio: realExecutionRatio },
          ]}
        />
        <PluginMaturityHeatmap
          data={[
            { plugin_name: "web_playwright", maturity_score: 0.8 },
            { plugin_name: "api_contract", maturity_score: 0.9 },
          ]}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Execution Path</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-lg font-medium capitalize">
            {run.execution_path || "standard"}
          </div>
          {run.parent_run_id && (
            <div className="text-sm text-muted-foreground mt-2">
              Escalated from: {run.parent_run_id.slice(0, 8)}
            </div>
          )}
        </CardContent>
      </Card>

      {run.metadata?.escalation_reason && (
        <Card>
          <CardHeader>
            <CardTitle>Escalation Reason</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">{run.metadata.escalation_reason}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
