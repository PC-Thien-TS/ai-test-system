"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ConfidenceScore } from "@/lib/types";

interface ConfidenceTrendChartProps {
  data: Array<{
    timestamp: string;
    confidence_score: number;
  }>;
}

export function ConfidenceTrendChart({ data }: ConfidenceTrendChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Trend</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <XAxis
              dataKey="timestamp"
              tickFormatter={(value: string) => new Date(value).toLocaleDateString()}
            />
            <YAxis domain={[0, 1]} />
            <Tooltip
              labelFormatter={(value: string) => new Date(value).toLocaleString()}
              formatter={(value: number) => [value.toFixed(2), "Confidence Score"]}
            />
            <Line
              type="monotone"
              dataKey="confidence_score"
              stroke="#8884d8"
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
