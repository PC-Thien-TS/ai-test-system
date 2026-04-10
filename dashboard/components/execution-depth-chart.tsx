"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface ExecutionDepthChartProps {
  data: Array<{
    plugin_name: string;
    depth_score: number;
  }>;
}

export function ExecutionDepthChart({ data }: ExecutionDepthChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plugin Execution Depth</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical">
            <XAxis type="number" domain={[0, 1]} />
            <YAxis dataKey="plugin_name" type="category" width={120} />
            <Tooltip
              formatter={(value: number) => [value.toFixed(2), "Depth Score"]}
            />
            <Bar dataKey="depth_score" fill="#82ca9d" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
