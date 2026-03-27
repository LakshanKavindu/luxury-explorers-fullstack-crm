import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { getContacts, deleteContact } from '../api/contactApi';
import type { Contact, PaginatedResponse } from '../types/crm';

import './Contacts.css';
import ContactModal from '../components/ContactModal';

export default function Contacts() {
  const user = useAuthStore((state) => state.user);

  // State
  const [data, setData] = useState<PaginatedResponse<Contact> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedContact, setSelectedContact] = useState<Contact | undefined>(undefined);

  // Permissions
  const canEdit = user?.role === 'admin' || user?.role === 'manager';
  const canDelete = user?.role === 'admin';

  const fetchContacts = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const res = await getContacts({
        search: searchTerm,
        page,
        page_size: pageSize,
        ordering: '-created_at'
      });
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch contacts. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, page, pageSize]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchContacts();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [fetchContacts]);

  const handleDelete = async (contact: Contact) => {
    if (!window.confirm(`Are you sure you want to delete ${contact.full_name}?`)) return;

    try {
      await deleteContact(contact.id);
      if (data?.results.length === 1 && page > 1) {
        setPage(page - 1);
      } else {
        fetchContacts();
      }
    } catch (err) {
      alert('Failed to delete contact.');
    }
  };

  const openEditModal = (contact: Contact) => {
    setSelectedContact(contact);
    setIsModalOpen(true);
  };

  const handleModalClose = (wasSaved: boolean) => {
    setIsModalOpen(false);
    if (wasSaved) {
      fetchContacts();
    }
  };

  return (
    <div className="contactsContainer">
      <div className="pageHeader">
        <div className="pageTitle">
          <h1>Contacts</h1>
          <p>Manage people across all companies in your organization.</p>
        </div>

        <div className="controlsRow">
          <input
            type="text"
            placeholder="Search by name, email, or role..."
            className="searchInput"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
          />
          {/* Note: Contact creation from global list requires selecting a company. 
              Implementing create logic in a follow-up if needed. */}
        </div>
      </div>

      {error ? (
        <div style={{ color: '#ef4444', padding: '20px', background: '#fef2f2', borderRadius: '8px' }}>
          {error}
        </div>
      ) : loading && !data ? (
        <div className="loadingState">
          <div className="spinner"></div>
        </div>
      ) : (
        <div className="tableCard">
          <table className="contactTable">
            <thead>
              <tr>
                <th>Contact Name</th>
                <th>Company</th>
                <th>Email</th>
                <th>Role</th>
                <th>Created</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.results.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="emptyState">No contacts found.</div>
                  </td>
                </tr>
              ) : (
                data?.results.map(contact => (
                  <tr key={contact.id}>
                    <td>
                      <div className="boldText">{contact.full_name}</div>
                    </td>
                    <td>{contact.company_detail?.name || '-'}</td>
                    <td>{contact.email}</td>
                    <td>
                      <span className="roleBadge">{contact.role || 'Member'}</span>
                    </td>
                    <td>{contact.created_at ? new Date(contact.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                      <div className="actionsCell">
                        {canEdit && (
                          <button className="iconBtn" onClick={() => openEditModal(contact)} title="Edit">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                          </button>
                        )}
                        {canDelete && (
                          <button className="iconBtn delete" onClick={() => handleDelete(contact)} title="Delete">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {data && data.total_pages > 1 && (
            <div className="pagination">
              <div className="pageInfo">
                Showing {Math.min((page - 1) * pageSize + 1, data.count)} to {Math.min(page * pageSize, data.count)} of {data.count} entries
              </div>
              <div className="pageControls">
                <button className="pageBtn" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
                <button className="pageBtn" disabled={page === data.total_pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {isModalOpen && selectedContact && (
        <ContactModal
          isOpen={isModalOpen}
          contact={selectedContact}
          companyId={selectedContact.company_detail?.id || ''}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
