"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { EscalationPolicy } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Save, Settings } from "lucide-react";

interface EscalationPolicyFormProps {
  projectId: string;
  policy?: EscalationPolicy;
}

export function EscalationPolicyForm({ projectId, policy }: EscalationPolicyFormProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<EscalationPolicy>(
    policy || {
      fallback_threshold: 0.5,
      confidence_threshold: 0.7,
      max_escalation_depth: 3,
      auto_escalate_on_fail: true,
      auto_escalate_on_flaky: true,
      plugin_overrides: {},
    }
  );

  const updatePolicyMutation = useMutation({
    mutationFn: (policy: EscalationPolicy) => api.updateProjectEscalationPolicy(projectId, policy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const handleSave = () => {
    updatePolicyMutation.mutate(formData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Escalation Policy
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2">
          <Label htmlFor="fallback_threshold">Fallback Threshold</Label>
          <div className="flex items-center gap-2">
            <Input
              id="fallback_threshold"
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={formData.fallback_threshold}
              onChange={(e) => setFormData({ ...formData, fallback_threshold: parseFloat(e.target.value) || 0 })}
              className="flex-1"
            />
            <span className="text-sm text-muted-foreground w-8">0-1</span>
          </div>
          <p className="text-xs text-muted-foreground">Escalate if fallback ratio exceeds this threshold</p>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="confidence_threshold">Confidence Threshold</Label>
          <div className="flex items-center gap-2">
            <Input
              id="confidence_threshold"
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={formData.confidence_threshold}
              onChange={(e) => setFormData({ ...formData, confidence_threshold: parseFloat(e.target.value) || 0 })}
              className="flex-1"
            />
            <span className="text-sm text-muted-foreground w-8">0-1</span>
          </div>
          <p className="text-xs text-muted-foreground">Escalate if confidence score falls below this threshold</p>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="max_escalation_depth">Max Escalation Depth</Label>
          <Input
            id="max_escalation_depth"
            type="number"
            min="1"
            max="10"
            value={formData.max_escalation_depth}
            onChange={(e) => setFormData({ ...formData, max_escalation_depth: parseInt(e.target.value) || 1 })}
          />
          <p className="text-xs text-muted-foreground">Maximum number of escalation attempts per chain</p>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="auto_escalate_on_fail"
            checked={formData.auto_escalate_on_fail}
            onCheckedChange={(checked) => setFormData({ ...formData, auto_escalate_on_fail: checked as boolean })}
          />
          <Label htmlFor="auto_escalate_on_fail" className="cursor-pointer">
            Auto-escalate on gate failure
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="auto_escalate_on_flaky"
            checked={formData.auto_escalate_on_flaky}
            onCheckedChange={(checked) => setFormData({ ...formData, auto_escalate_on_flaky: checked as boolean })}
          />
          <Label htmlFor="auto_escalate_on_flaky" className="cursor-pointer">
            Auto-escalate on flaky results
          </Label>
        </div>

        <Button onClick={handleSave} disabled={updatePolicyMutation.isPending} className="w-full">
          <Save className="mr-2 h-4 w-4" />
          {updatePolicyMutation.isPending ? "Saving..." : "Save Policy"}
        </Button>
      </CardContent>
    </Card>
  );
}
