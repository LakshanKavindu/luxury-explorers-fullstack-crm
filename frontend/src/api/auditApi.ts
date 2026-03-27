import apiClient from "./axios";
import type { ActivityLog, PaginatedResponse, ActivityLogFilters } from "../types/crm";

const AUDIT_BASE = "/activity-logs/";

function cleanParams(params: ActivityLogFilters) {
  const cleaned: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      cleaned[key] = value;
    }
  }
  return cleaned;
}

export async function getLogs(params: ActivityLogFilters = {}): Promise<PaginatedResponse<ActivityLog>> {
  const response = await apiClient.get<PaginatedResponse<ActivityLog>>(AUDIT_BASE, {
    params: cleanParams(params),
  });
  return response.data;
}
