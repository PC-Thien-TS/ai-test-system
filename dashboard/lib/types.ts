// Type definitions matching the FastAPI backend models

export enum ProductType {
  WEB = "web",
  API = "api",
  MODEL = "model",
  RAG = "rag",
  LLM_APP = "llm_app",
  WORKFLOW = "workflow",
  DATA_PIPELINE = "data_pipeline",
}

export enum RunStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum GateResult {
  PASS = "pass",
  FAIL = "fail",
  WARN = "warn",
  UNKNOWN = "unknown",
}

export enum SupportLevel {
  FULL = "full",
  USABLE = "usable",
  PARTIAL = "partial",
  FALLBACK = "fallback",
  NONE = "none",
}

export interface Project {
  project_id: string;
  name: string;
  product_type: string;
  manifest_path: string;
  description?: string;
  tags: string[];
  workspace_id?: string;
  owner_id?: string;
  created_at: string;
  updated_at: string;
  active: boolean;
}

export interface Run {
  run_id: string;
  project_id: string;
  status: string;
  started_at: string;
  output_path: string;
  completed_at?: string;
  gate_result?: string;
  flaky: boolean;
  metadata?: Record<string, any>;
  execution_path?: string;
  parent_run_id?: string;
  confidence_score?: number;
  fallback_ratio?: number;
  real_execution_ratio?: number;
}

export interface PluginMetadata {
  name: string;
  version: string;
  description: string;
  product_types: string[];
  capabilities: string[];
  support_level: string;
  dependencies?: string[];
  min_platform_version?: string;
  execution_depth_score: number;
  evidence_richness_score: number;
  confidence_score: number;
}

export interface PlatformSummary {
  total_projects: number;
  active_projects: number;
  total_runs: number;
  failing_projects: number;
  flaky_projects: number;
  gate_overview: Record<string, number>;
  plugin_usage: Record<string, number>;
  generated_at: string;
  avg_execution_depth_score: number;
  avg_evidence_richness_score: number;
  avg_confidence_score: number;
  avg_fallback_ratio: number;
  avg_real_execution_ratio: number;
  plugin_maturity_trend: Record<string, number>;
  confidence_trend: Array<{ timestamp: string; confidence_score: number }>;
  plugin_depth_scores: Array<{ plugin_name: string; depth_score: number }>;
  fallback_ratios: Array<{ name: string; fallback_ratio: number; real_execution_ratio: number }>;
  plugin_maturity_scores: Array<{ plugin_name: string; maturity_score: number }>;
}

export interface ProjectSummary {
  project_id: string;
  project_name: string;
  product_type: string;
  latest_run_id?: string;
  latest_status?: string;
  gate_result?: string;
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  flaky_runs: number;
  last_updated?: string;
  avg_execution_depth_score: number;
  avg_evidence_richness_score: number;
  avg_confidence_score: number;
  avg_fallback_ratio: number;
  avg_real_execution_ratio: number;
}

export interface TrendDataPoint {
  run_id: string;
  timestamp: string;
  status: string;
  gate_result?: string;
  flaky: boolean;
  duration?: number;
}

export interface CompatibilitySummary {
  plugin_name: string;
  platform_version: string;
  compatible: boolean;
  support_level: string;
  notes: string[];
  blockers: string[];
}

export enum ExecutionPath {
  SMOKE = "smoke",
  STANDARD = "standard",
  DEEP = "deep",
  INTELLIGENT = "intelligent",
}

export interface ExecutionStrategy {
  path: ExecutionPath;
  reason: string;
  confidence_threshold: number;
  fallback_threshold: number;
  enable_negative_paths: boolean;
  enable_retry_rollback: boolean;
  enable_anomaly_detection: boolean;
  estimated_duration_multiplier: number;
}

export interface ConfidenceFactors {
  evidence_richness: number;
  run_stability: number;
  anomaly_free: number;
  historical_performance: number;
  plugin_maturity: number;
  fallback_penalty: number;
}

export interface ConfidenceScore {
  overall_score: number;
  factors: ConfidenceFactors;
  timestamp: string;
  notes: string[];
}

export interface EvidenceItem {
  evidence_type: string;
  timestamp: string;
  plugin_name: string;
  source: string;
  content: Record<string, any>;
  confidence: number;
  severity: string;
}

export interface EvidenceSummary {
  run_id: string;
  plugin_name: string;
  total_evidence_count: number;
  evidence_by_type: Record<string, number>;
  avg_confidence: number;
  richness_score: number;
  critical_findings: EvidenceItem[];
  warnings: EvidenceItem[];
}

export interface EscalationReason {
  timestamp: string;
  from_path: ExecutionPath;
  to_path: ExecutionPath;
  reason: string;
  metrics_snapshot: Record<string, number>;
}
