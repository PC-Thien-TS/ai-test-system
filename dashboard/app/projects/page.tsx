"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProductType, GateResult } from "@/lib/types";
import { Search, Filter, ArrowUpDown, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [productTypeFilter, setProductTypeFilter] = useState<string>("all");
  const [gateResultFilter, setGateResultFilter] = useState<string>("all");

  const { data: projects, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center p-8">
        <div className="max-w-md text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error loading projects</h2>
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

  const filteredProjects = projects?.filter((project) => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesProductType = productTypeFilter === "all" || project.product_type === productTypeFilter;
    // Note: gate result filtering would need to be done via summary API
    const matchesGateResult = gateResultFilter === "all";
    return matchesSearch && matchesProductType && matchesGateResult;
  }) || [];

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-3xl font-bold">Projects</h1>
        <p className="text-muted-foreground">Manage and view all testing projects</p>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-4 py-2 w-full border rounded-md"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={productTypeFilter}
            onChange={(e) => setProductTypeFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="all">All Types</option>
            {Object.values(ProductType).map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <select
            value={gateResultFilter}
            onChange={(e) => setGateResultFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="all">All Gate Results</option>
            {Object.values(GateResult).map((result) => (
              <option key={result} value={result}>
                {result}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4">
        {filteredProjects.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center h-48">
              <p className="text-muted-foreground">No projects found</p>
            </CardContent>
          </Card>
        ) : (
          filteredProjects.map((project) => (
            <Card key={project.project_id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <h3 className="text-lg font-semibold">{project.name}</h3>
                    <div className="flex gap-4 text-sm text-muted-foreground">
                      <span>Type: {project.product_type}</span>
                      {project.workspace_id && <span>Workspace: {project.workspace_id}</span>}
                      <span>Runs: {project.active ? "Active" : "Inactive"}</span>
                    </div>
                    {project.description && (
                      <p className="text-sm text-muted-foreground">{project.description}</p>
                    )}
                  </div>
                  <Link href={`/projects/${project.project_id}`}>
                    <Button variant="outline" size="sm">
                      View Details
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
