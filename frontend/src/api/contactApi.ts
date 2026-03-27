import apiClient from "./axios";
import type { Contact, PaginatedResponse, ContactListFilters } from "../types/crm";

const CONTACTS_BASE = "/contacts/";

/**
 * Clean up empty params
 */
function cleanParams(params: ContactListFilters) {
  const cleaned: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      cleaned[key] = value;
    }
  }
  return cleaned;
}

export async function getContacts(params: ContactListFilters = {}): Promise<PaginatedResponse<Contact>> {
  const response = await apiClient.get<PaginatedResponse<Contact>>(CONTACTS_BASE, {
    params: cleanParams(params),
  });
  return response.data;
}

export async function getContact(id: string): Promise<Contact> {
  const response = await apiClient.get<Contact>(`${CONTACTS_BASE}${id}/`);
  return response.data;
}

export async function createContact(data: Partial<Contact>): Promise<Contact> {
  const response = await apiClient.post<Contact>(CONTACTS_BASE, data);
  return response.data;
}

export async function updateContact(id: string, data: Partial<Contact>): Promise<Contact> {
  const response = await apiClient.patch<Contact>(`${CONTACTS_BASE}${id}/`, data);
  return response.data;
}

export async function deleteContact(id: string): Promise<void> {
  await apiClient.delete(`${CONTACTS_BASE}${id}/`);
}
