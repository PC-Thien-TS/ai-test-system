"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, GitCompare, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function EvidenceComparisonPage() {
  const params = useParams();
  const runAId = params.runAId as string;
  const runBId = params.runBId as string;

  const { data: runA, isLoading: loadingA } = useQuery({
    queryKey: ["run", runAId],
    queryFn: () => api.getRun(runAId),
    enabled: !!runAId,
  });

  const { data: runB, isLoading: loadingB } = useQuery({
    queryKey: ["run", runBId],
    queryFn: () => api.getRun(runBId),
    enabled: !!runBId,
  });

  if (loadingA || loadingB) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!runA || !runB) {
    return <div className="flex h-screen items-center justify-center">Run not found</div>;
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center gap-4">
        <Link href={`/evidence/${runBId}`}>
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Evidence
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Evidence Comparison</h1>
          <p className="text-muted-foreground">
            Comparing escalation runs {runAId.slice(0, 8)} and {runBId.slice(0, 8)}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run Comparison Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border p-4 rounded-lg">
              <div className="font-medium mb-2">Run A (Parent)</div>
              <div className="text-sm text-muted-foreground mb-2">ID: {runAId.slice(0, 8)}</div>
              <div className="text-sm">Path: {runA.execution_path}</div>
              <div className="text-sm">Confidence: {runA.confidence_score?.toFixed(2)}</div>
              <div className="text-sm">Fallback: {runA.fallback_ratio?.toFixed(2)}</div>
            </div>
            <div className="border p-4 rounded-lg">
              <div className="font-medium mb-2">Run B (Escalated)</div>
              <div className="text-sm text-muted-foreground mb-2">ID: {runBId.slice(0, 8)}</div>
              <div className="text-sm">Path: {runB.execution_path}</div>
              <div className="text-sm">Confidence: {runB.confidence_score?.toFixed(2)}</div>
              <div className="text-sm">Fallback: {runB.fallback_ratio?.toFixed(2)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evidence Differences</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No evidence comparison data available yet.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Side-by-Side Evidence View</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border p-4 rounded-lg">
              <div className="font-medium mb-4">Run A Evidence</div>
              <div className="text-sm text-muted-foreground">No evidence items</div>
            </div>
            <div className="border p-4 rounded-lg">
              <div className="font-medium mb-4">Run B Evidence</div>
              <div className="text-sm text-muted-foreground">No evidence items</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
