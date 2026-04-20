// API client for the Universal Testing Platform backend
import type {
  CompatibilitySummary,
  EscalationPolicy,
  PlatformSummary,
  PluginMetadata,
  Project,
  ProjectSummary,
  Run,
  TrendDataPoint,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`[API] GET ${url}`);
    try {
      const response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "test-user",
          "X-User-Role": "viewer",
        },
      });
      console.log(`[API] Response status: ${response.status}`);
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API] Error response:`, errorText);
        throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
      }
      return response.json();
    } catch (error) {
      console.error(`[API] Request failed:`, error);
      throw error;
    }
  },

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`[API] POST ${url}`);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "test-user",
          "X-User-Role": "maintainer",
        },
        body: JSON.stringify(data),
      });
      console.log(`[API] Response status: ${response.status}`);
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API] Error response:`, errorText);
        throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
      }
      return response.json();
    } catch (error) {
      console.error(`[API] Request failed:`, error);
      throw error;
    }
  },
};

// API functions
export const api = {
  // Health
  getHealth: () => apiClient.get<{ status: string; version: string; service: string }>("/health/"),

  // Platform
  getPlatformSummary: () => apiClient.get<PlatformSummary>("/platform/summary"),
  getLatestProjectStatus: () => apiClient.get<ProjectSummary[]>("/platform/projects/latest"),

  // Projects
  listProjects: (workspaceId?: string, activeOnly = true) => {
    const params = new URLSearchParams();
    if (workspaceId) {
      const wsId =
        typeof workspaceId === "object"
          ? String((workspaceId as { id?: string }).id ?? "")
          : String(workspaceId);

      if (wsId) params.append("workspace_id", wsId);
    }
    if (activeOnly) params.append("active_only", "true");
    const query = params.toString();
    return apiClient.get<Project[]>(`/projects/${query ? `?${query}` : ""}`);
  },
  getProject: (projectId: string) => apiClient.get<Project>(`/projects/${projectId}`),
  createProject: (data: {
    name: string;
    product_type: string;
    manifest_path: string;
    description?: string;
    tags?: string[];
    workspace_id?: string;
  }) => apiClient.post<Project>("/projects", data),
  updateProjectEscalationPolicy: (projectId: string, policy: EscalationPolicy) =>
    apiClient.post<Project>(`/projects/${projectId}/escalation-policy`, policy),
  triggerRun: (projectId: string) =>
    apiClient.post<{ run_id: string; project_id: string; status: string; output_path: string; started_at: string }>(
      `/projects/${projectId}/run`,
      {}
    ),

  // Runs
  listRuns: (projectId: string, limit = 50) =>
    apiClient.get<Run[]>(`/projects/${projectId}/runs?limit=${limit}`),
  getRun: (runId: string) => apiClient.get<Run>(`/runs/${runId}`),
  getProjectSummary: (projectId: string) =>
    apiClient.get<ProjectSummary>(`/projects/${projectId}/summary`),
  getProjectTrends: (projectId: string, limit = 50) =>
    apiClient.get<TrendDataPoint[]>(`/projects/${projectId}/trends?limit=${limit}`),

  // Plugins
  listPlugins: (productType?: string) => {
    if (productType) {
      return apiClient.get<PluginMetadata[]>(`/plugins?product_type=${productType}`);
    }
    return apiClient.get<PluginMetadata[]>("/plugins");
  },
  getPlugin: (pluginName: string) => apiClient.get<PluginMetadata>(`/plugins/${pluginName}`),
  getPluginCompatibility: (pluginName: string) =>
    apiClient.get<CompatibilitySummary>(`/plugins/${pluginName}/compatibility`),
};
