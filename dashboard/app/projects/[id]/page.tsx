"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Play, Clock, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ConfidenceTrendChart } from "@/components/confidence-trend-chart";
import { ExecutionDepthChart } from "@/components/execution-depth-chart";
import { FallbackRatioHeatmap } from "@/components/fallback-ratio-heatmap";
import { PluginMaturityHeatmap } from "@/components/plugin-maturity-heatmap";
import { EscalationPolicyForm } from "@/components/escalation-policy-form";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !!projectId,
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["project-summary", projectId],
    queryFn: () => api.getProjectSummary(projectId),
    enabled: !!projectId,
  });

  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ["project-trends", projectId],
    queryFn: () => api.getProjectTrends(projectId, 50),
    enabled: !!projectId,
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["project-runs", projectId],
    queryFn: () => api.listRuns(projectId, 20),
    enabled: !!projectId,
  });

  if (projectLoading || summaryLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!project) {
    return <div className="flex h-screen items-center justify-center">Project not found</div>;
  }

  const trendData = trends?.map((t) => ({
    ...t,
    timestamp: new Date(t.timestamp).toLocaleDateString(),
  })) || [];

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center gap-4">
        <Link href="/projects">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">{project.name}</h1>
          <p className="text-muted-foreground">{project.description || "No description"}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_runs || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Passed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{summary?.passed_runs || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary?.failed_runs || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Flaky</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{summary?.flaky_runs || 0}</div>
          </CardContent>
        </Card>
      </div>

      {trendData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Run Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="duration" stroke="#8884d8" name="Duration (s)" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <ConfidenceTrendChart
          data={trendData.map(t => ({
            timestamp: t.timestamp,
            confidence_score: t.gate_result === "pass" ? 0.9 : 0.3,
          }))}
        />
        <ExecutionDepthChart
          data={[
            { name: project.name, execution_depth_score: 0.75 },
          ]}
        />
        <FallbackRatioHeatmap
          data={[
            { name: project.name, fallback_ratio: 0.2, real_execution_ratio: 0.8 },
          ]}
        />
        <PluginMaturityHeatmap
          data={project.tags.map(tag => ({
            plugin_name: tag,
            maturity_score: 0.8,
          }))}
        />
      </div>

      <EscalationPolicyForm projectId={projectId} policy={project.escalation_policy} />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Runs</CardTitle>
            <Button size="sm">
              <Play className="mr-2 h-4 w-4" />
              Trigger Run
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <div className="text-center py-4">Loading runs...</div>
          ) : runs && runs.length > 0 ? (
            <div className="space-y-2">
              {runs.map((run) => (
                <div key={run.run_id} className="flex items-center justify-between border p-3 rounded-lg">
                  <div className="flex items-center gap-4">
                    {run.status === "completed" && run.gate_result === "pass" && (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    )}
                    {run.status === "completed" && run.gate_result === "fail" && (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    {run.status === "failed" && <XCircle className="h-5 w-5 text-red-600" />}
                    {run.status === "pending" && <Clock className="h-5 w-5 text-yellow-600" />}
                    {run.flaky && <AlertTriangle className="h-5 w-5 text-yellow-600" />}
                    <div>
                      <div className="font-medium">{run.run_id}</div>
                      <div className="text-sm text-muted-foreground">
                        {new Date(run.started_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-sm">
                    <span className="capitalize">{run.status}</span>
                    {run.gate_result && (
                      <span className="ml-2 capitalize">- {run.gate_result}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4 text-muted-foreground">No runs yet</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
