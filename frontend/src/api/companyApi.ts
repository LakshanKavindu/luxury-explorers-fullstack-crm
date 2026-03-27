/**
 * API client for Company operations.
 * Handles both JSON GET/DELETE requests and FormData POST/PATCH/PUT requests.
 */
import apiClient from "./axios";
import type { Company, PaginatedResponse, CompanyListFilters } from "../types/crm";

const COMPANIES_BASE = "/crm/companies/";

/**
 * Clean up empty strings or undefined from query params so they don't get sent.
 */
function cleanParams(params: CompanyListFilters) {
  const cleaned: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      cleaned[key] = value;
    }
  }
  return cleaned;
}

/**
 * Get paginated list of companies.
 */
export async function getCompanies(params: CompanyListFilters = {}): Promise<PaginatedResponse<Company>> {
  const response = await apiClient.get<PaginatedResponse<Company>>(COMPANIES_BASE, {
    params: cleanParams(params),
  });
  // Since CompanyViewSet is a standard DRF view, we assume it returns the paginated shape directly.
  return response.data;
}

/**
 * Get a single company by ID.
 */
export async function getCompany(id: string): Promise<Company> {
  const response = await apiClient.get<Company>(`${COMPANIES_BASE}${id}/`);
  return response.data;
}

/**
 * Create a new company.
 * Uses FormData to support `logo` file uploads.
 */
export async function createCompany(data: FormData): Promise<Company> {
  const response = await apiClient.post<Company>(COMPANIES_BASE, data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

/**
 * Update an existing company (Partial Update).
 * Uses FormData to support `logo` file uploads.
 */
export async function updateCompany(id: string, data: FormData): Promise<Company> {
  const response = await apiClient.patch<Company>(`${COMPANIES_BASE}${id}/`, data, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

/**
 * Soft delete a company.
 * Only Admins have access to this endpoint.
 */
export async function deleteCompany(id: string): Promise<void> {
  await apiClient.delete(`${COMPANIES_BASE}${id}/`);
}
