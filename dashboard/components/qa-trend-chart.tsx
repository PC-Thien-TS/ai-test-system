"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type TrendLineConfig = {
  key: string;
  label: string;
  color: string;
};

type QaTrendChartProps = {
  title: string;
  description?: string;
  data: Array<Record<string, string | number | null>>;
  lines: TrendLineConfig[];
  yDomain?: [number, number] | ["auto", "auto"];
};

function formatTimestamp(value: unknown): string {
  if (typeof value !== "string") {
    return "N/A";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
}

export function QaTrendChart({ title, description, data, lines, yDomain = ["auto", "auto"] }: QaTrendChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTimestamp}
              minTickGap={24}
            />
            <YAxis domain={yDomain} allowDecimals={false} />
            <Tooltip
              labelFormatter={(label) => {
                if (typeof label !== "string") {
                  return String(label);
                }
                const parsed = new Date(label);
                return Number.isNaN(parsed.getTime()) ? label : parsed.toLocaleString();
              }}
            />
            {lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.label}
                stroke={line.color}
                strokeWidth={2}
                connectNulls
                dot={{ r: 3 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
