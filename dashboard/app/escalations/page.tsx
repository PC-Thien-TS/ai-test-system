"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, TrendingUp, AlertCircle } from "lucide-react";
import Link from "next/link";

export default function EscalationsPage() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Escalation Browser</h1>
          <p className="text-muted-foreground">View escalation chains and path promotions</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Escalation Chains</CardTitle>
        </CardHeader>
        <CardContent>
          {projects && projects.length > 0 ? (
            <div className="space-y-4">
              {projects.map((project) => (
                <div key={project.project_id} className="border p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-medium">{project.name}</div>
                    <div className="text-sm text-muted-foreground">{project.product_type}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    No escalation chains found for this project yet.
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No projects found. Escalation chains will appear here after runs are escalated.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Escalation Path Promotions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="border p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">SMOKE → STANDARD</span>
              </div>
              <div className="text-2xl font-bold">0</div>
              <div className="text-xs text-muted-foreground">Escalations</div>
            </div>
            <div className="border p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">STANDARD → DEEP</span>
              </div>
              <div className="text-2xl font-bold">0</div>
              <div className="text-xs text-muted-foreground">Escalations</div>
            </div>
            <div className="border p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium">DEEP → INTELLIGENT</span>
              </div>
              <div className="text-2xl font-bold">0</div>
              <div className="text-xs text-muted-foreground">Escalations</div>
            </div>
            <div className="border p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <span className="text-sm font-medium">Max Depth Reached</span>
              </div>
              <div className="text-2xl font-bold">0</div>
              <div className="text-xs text-muted-foreground">Escalations</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
