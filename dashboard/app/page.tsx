"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, CheckCircle, XCircle, AlertTriangle, FolderOpen, Play } from "lucide-react";

export default function PlatformOverviewPage() {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ["platform-summary"],
    queryFn: api.getPlatformSummary,
  });

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center p-8">
        <div className="max-w-md text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error loading platform summary</h2>
          <p className="text-sm text-muted-foreground mb-4">
            {error instanceof Error ? error.message : String(error)}
          </p>
          <p className="text-xs text-muted-foreground">
            API URL: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
          </p>
        </div>
      </div>
    );
  }

  const metrics = [
    {
      title: "Total Projects",
      value: summary?.total_projects || 0,
      icon: FolderOpen,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
    },
    {
      title: "Active Projects",
      value: summary?.active_projects || 0,
      icon: CheckCircle,
      color: "text-green-600",
      bgColor: "bg-green-50",
    },
    {
      title: "Total Runs",
      value: summary?.total_runs || 0,
      icon: Play,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
    },
    {
      title: "Failing Projects",
      value: summary?.failing_projects || 0,
      icon: XCircle,
      color: "text-red-600",
      bgColor: "bg-red-50",
    },
    {
      title: "Flaky Projects",
      value: summary?.flaky_projects || 0,
      icon: AlertTriangle,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
    },
  ];

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-3xl font-bold">Platform Overview</h1>
        <p className="text-muted-foreground">
          Last updated: {summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "N/A"}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {metrics.map((metric) => (
          <Card key={metric.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
              <div className={`${metric.bgColor} p-2 rounded-lg`}>
                <metric.icon className={`h-4 w-4 ${metric.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quality Gate Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.gate_overview && Object.keys(summary.gate_overview).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(summary.gate_overview).map(([gate, count]) => (
                  <div key={gate} className="flex justify-between items-center">
                    <span className="capitalize">{gate}</span>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">No gate data available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Plugin Usage</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.plugin_usage && Object.keys(summary.plugin_usage).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(summary.plugin_usage).map(([plugin, count]) => (
                  <div key={plugin} className="flex justify-between items-center">
                    <span className="capitalize">{plugin}</span>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">No plugin data available</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
