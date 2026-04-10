"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunStatus, GateResult } from "@/lib/types";
import { Clock, CheckCircle, XCircle, AlertTriangle, Hourglass, StopCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function RunsExplorerPage() {
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  // Get all runs from all projects
  const { data: allRuns, isLoading: runsLoading } = useQuery({
    queryKey: ["all-runs"],
    queryFn: async () => {
      if (!projects) return [];
      const runsPromises = projects.map((project) =>
        api.listRuns(project.project_id, 10)
      );
      const results = await Promise.all(runsPromises);
      return results.flat().map((run, index) => ({
        ...run,
        projectName: projects[index % projects.length].name,
        projectType: projects[index % projects.length].product_type,
      }));
    },
    enabled: !!projects && projects.length > 0,
  });

  if (projectsLoading || runsLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  // Handle errors
  if (!projects && !projectsLoading) {
    return (
      <div className="flex h-screen items-center justify-center p-8">
        <div className="max-w-md text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error loading projects</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Unable to load projects. Check if the backend is running.
          </p>
          <p className="text-xs text-muted-foreground">
            API URL: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
          </p>
        </div>
      </div>
    );
  }

  const runs = allRuns || [];

  const getStatusIcon = (status: string, gateResult?: string, flaky = false) => {
    if (flaky) return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
    if (status === "completed" && gateResult === "pass") return <CheckCircle className="h-5 w-5 text-green-600" />;
    if (status === "completed" && gateResult === "fail") return <XCircle className="h-5 w-5 text-red-600" />;
    if (status === "failed") return <XCircle className="h-5 w-5 text-red-600" />;
    if (status === "running") return <Clock className="h-5 w-5 text-blue-600" />;
    if (status === "pending") return <Hourglass className="h-5 w-5 text-yellow-600" />;
    if (status === "cancelled") return <StopCircle className="h-5 w-5 text-gray-600" />;
    return <Clock className="h-5 w-5 text-gray-600" />;
  };

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-3xl font-bold">Runs Explorer</h1>
        <p className="text-muted-foreground">View and explore test runs across all projects</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Runs ({runs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No runs found. Create a project and trigger a run to see results here.
            </div>
          ) : (
            <div className="space-y-2">
              {runs.map((run: any) => (
                <div key={run.run_id} className="flex items-center justify-between border p-4 rounded-lg hover:bg-accent">
                  <div className="flex items-center gap-4">
                    {getStatusIcon(run.status, run.gate_result, run.flaky)}
                    <div>
                      <div className="font-medium">{run.projectName}</div>
                      <div className="text-sm text-muted-foreground">
                        Run ID: {run.run_id} • Type: {run.projectType}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Started {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium capitalize">{run.status}</div>
                    {run.gate_result && (
                      <div className="text-xs text-muted-foreground capitalize">
                        Gate: {run.gate_result}
                      </div>
                    )}
                    {run.duration && (
                      <div className="text-xs text-muted-foreground">
                        {Math.round(run.duration)}s
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
