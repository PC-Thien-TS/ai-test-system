import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrendState } from "@/lib/qa-command-center-trends";

type QaKpiCardProps = {
  title: string;
  value: string | number;
  subtitle?: string;
  deltaText?: string;
  trendState?: TrendState;
};

function trendClassName(state: TrendState | undefined): string {
  if (state === "improving") return "text-green-700";
  if (state === "worsening") return "text-red-700";
  if (state === "stable") return "text-slate-700";
  return "text-slate-500";
}

function TrendIcon({ state }: { state: TrendState | undefined }) {
  if (state === "improving") return <ArrowUpRight className="h-4 w-4" />;
  if (state === "worsening") return <ArrowDownRight className="h-4 w-4" />;
  return <ArrowRight className="h-4 w-4" />;
}

export function QaKpiCard({ title, value, subtitle, deltaText, trendState }: QaKpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-3xl font-bold">{String(value)}</p>
        {subtitle ? <p className="text-xs text-muted-foreground">{subtitle}</p> : null}
        {deltaText ? (
          <p className={`inline-flex items-center gap-1 text-xs font-medium ${trendClassName(trendState)}`}>
            <TrendIcon state={trendState} />
            {deltaText}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
