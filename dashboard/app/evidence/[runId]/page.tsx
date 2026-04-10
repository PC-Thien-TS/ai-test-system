"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Search, Image, FileText, AlertTriangle, CheckCircle, Download, GitCompare } from "lucide-react";
import Link from "next/link";

export default function EvidenceBrowserPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterPlugin, setFilterPlugin] = useState<string>("all");
  const [minConfidence, setMinConfidence] = useState<number>(0);

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    enabled: !!runId,
  });

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!run) {
    return <div className="flex h-screen items-center justify-center">Run not found</div>;
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/runs/${runId}`}>
            <Button variant="outline" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Run
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Evidence Browser</h1>
            <p className="text-muted-foreground">Run {runId.slice(0, 8)}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {run.parent_run_id && (
            <Link href={`/evidence/compare/${run.parent_run_id}/${runId}`}>
              <Button variant="outline" size="sm">
                <GitCompare className="mr-2 h-4 w-4" />
                Compare Escalation
              </Button>
            </Link>
          )}
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Download All
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Advanced Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search evidence..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border rounded-md px-3 py-2"
            >
              <option value="all">All Types</option>
              <option value="screenshot">Screenshots</option>
              <option value="trace">Traces</option>
              <option value="citation">Citations</option>
              <option value="anomaly">Anomalies</option>
              <option value="matrix">Matrices</option>
            </select>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="border rounded-md px-3 py-2"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              value={filterPlugin}
              onChange={(e) => setFilterPlugin(e.target.value)}
              className="border rounded-md px-3 py-2"
            >
              <option value="all">All Plugins</option>
              <option value="web_playwright">Web Playwright</option>
              <option value="api_contract">API Contract</option>
              <option value="model_eval">Model Eval</option>
            </select>
            <div className="flex items-center gap-2">
              <label className="text-sm">Min Confidence:</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm w-12">{minConfidence}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image className="h-4 w-4" />
              Screenshots
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <div className="text-sm text-muted-foreground">Captured during execution</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Traces
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <div className="text-sm text-muted-foreground">Execution traces</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Citations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <div className="text-sm text-muted-foreground">Grounding citations</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              Anomalies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <div className="text-sm text-muted-foreground">Detected anomalies</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Matrices
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <div className="text-sm text-muted-foreground">Test matrices</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Evidence Items</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No evidence items found. Evidence will be available after run completion.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
