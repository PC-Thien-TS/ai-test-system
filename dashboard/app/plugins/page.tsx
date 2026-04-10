"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProductType, SupportLevel } from "@/lib/types";
import { Puzzle, CheckCircle, AlertTriangle, XCircle, Info } from "lucide-react";

export default function PluginsPage() {
  const [selectedProductType, setSelectedProductType] = useState<string>("all");

  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ["plugins", selectedProductType],
    queryFn: () => api.listPlugins(selectedProductType === "all" ? undefined : selectedProductType),
  });

  const getSupportLevelIcon = (level: string) => {
    switch (level) {
      case "full":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "usable":
        return <CheckCircle className="h-5 w-5 text-blue-600" />;
      case "partial":
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case "fallback":
        return <AlertTriangle className="h-5 w-5 text-orange-600" />;
      case "none":
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Info className="h-5 w-5 text-gray-600" />;
    }
  };

  const getSupportLevelColor = (level: string) => {
    switch (level) {
      case "full":
        return "text-green-600 bg-green-50";
      case "usable":
        return "text-blue-600 bg-blue-50";
      case "partial":
        return "text-yellow-600 bg-yellow-50";
      case "fallback":
        return "text-orange-600 bg-orange-50";
      case "none":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center p-8">
        <div className="max-w-md text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error loading plugins</h2>
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

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-3xl font-bold">Plugin Catalog</h1>
        <p className="text-muted-foreground">Browse and manage testing plugins</p>
      </div>

      <div className="flex gap-4 items-center">
        <label className="text-sm font-medium">Filter by Product Type:</label>
        <select
          value={selectedProductType}
          onChange={(e) => setSelectedProductType(e.target.value)}
          className="px-4 py-2 border rounded-md"
        >
          <option value="all">All Types</option>
          {Object.values(ProductType).map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plugins?.map((plugin) => (
          <Card key={plugin.name}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{plugin.name}</CardTitle>
                <div className={`p-2 rounded-lg ${getSupportLevelColor(plugin.support_level)}`}>
                  {getSupportLevelIcon(plugin.support_level)}
                </div>
              </div>
              <div className="text-sm text-muted-foreground">v{plugin.version}</div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm">{plugin.description}</p>
              
              <div>
                <div className="text-xs font-semibold mb-2">Product Types</div>
                <div className="flex flex-wrap gap-1">
                  {plugin.product_types.map((type) => (
                    <span key={type} className="text-xs px-2 py-1 bg-secondary rounded">
                      {type}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold mb-2">Capabilities</div>
                <div className="flex flex-wrap gap-1">
                  {plugin.capabilities.map((cap) => (
                    <span key={cap} className="text-xs px-2 py-1 bg-accent rounded">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                <div>Support Level: <span className="capitalize font-medium">{plugin.support_level}</span></div>
                {plugin.min_platform_version && (
                  <div>Min Platform: {plugin.min_platform_version}</div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {plugins && plugins.length === 0 && (
        <Card>
          <CardContent className="flex items-center justify-center h-48">
            <p className="text-muted-foreground">No plugins found for this product type</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
