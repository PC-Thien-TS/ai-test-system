"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface PluginMaturityHeatmapProps {
  data: Array<{
    plugin_name: string;
    maturity_score: number;
  }>;
}

const getMaturityColor = (score: number) => {
  if (score >= 0.8) return "#10b981"; // green
  if (score >= 0.6) return "#3b82f6"; // blue
  if (score >= 0.4) return "#f59e0b"; // yellow
  return "#ef4444"; // red
};

export function PluginMaturityHeatmap({ data }: PluginMaturityHeatmapProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plugin Maturity Scores</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <XAxis dataKey="plugin_name" />
            <YAxis domain={[0, 1]} />
            <Tooltip
              formatter={(value: number) => [value.toFixed(2), "Maturity Score"]}
            />
            <Area
              type="monotone"
              dataKey="maturity_score"
              stroke="#8884d8"
              fill="#8884d8"
              fillOpacity={0.6}
            />
          </AreaChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 gap-4 mt-4">
          {data.map((item) => (
            <div key={item.plugin_name} className="flex items-center justify-between p-2 rounded bg-muted">
              <span className="text-sm font-medium">{item.plugin_name}</span>
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getMaturityColor(item.maturity_score) }}
                />
                <span className="text-sm">{item.maturity_score.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
