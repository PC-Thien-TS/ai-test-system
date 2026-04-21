"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface FallbackRatioHeatmapProps {
  data: Array<{
    name: string;
    fallback_ratio: number;
    real_execution_ratio: number;
  }>;
}

const COLORS = {
  low: "#82ca9d", // green
  medium: "#ffc658", // yellow
  high: "#ff7300", // orange
  critical: "#ff0000", // red
};

const getFallbackColor = (ratio: number) => {
  if (ratio < 0.2) return COLORS.low;
  if (ratio < 0.4) return COLORS.medium;
  if (ratio < 0.6) return COLORS.high;
  return COLORS.critical;
};

export function FallbackRatioHeatmap({ data }: FallbackRatioHeatmapProps) {
  const pieData = data.map((item) => ({
    name: item.name,
    value: item.fallback_ratio,
    color: getFallbackColor(item.fallback_ratio),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fallback Ratio Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [value.toFixed(2), "Fallback Ratio"]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#82ca9d]" />
            <span>Low (&lt;0.2)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ffc658]" />
            <span>Medium (0.2-0.4)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff7300]" />
            <span>High (0.4-0.6)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff0000]" />
            <span>Critical (&gt;0.6)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
