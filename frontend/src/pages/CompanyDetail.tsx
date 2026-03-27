import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getCompany } from '../api/companyApi';
import { getContacts, deleteContact } from '../api/contactApi';
import type { Company, Contact, PaginatedResponse } from '../types/crm';
import ContactModal from '../components/ContactModal';
import './CompanyDetail.css';

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((state) => state.user);
  
  const [company, setCompany] = useState<Company | null>(null);
  const [contactsData, setContactsData] = useState<PaginatedResponse<Contact> | null>(null);
  
  const [loadingCompany, setLoadingCompany] = useState(true);
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & Search for Contacts
  const [page, setPage] = useState(1);
  const pageSize = 50; // We can load a large page size for a grid, or implement load-more

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedContact, setSelectedContact] = useState<Contact | undefined>(undefined);

  // Permissions
  const canEdit = user?.role === 'admin' || user?.role === 'manager';
  const canDelete = user?.role === 'admin';

  // Fetch Core Company Info
  useEffect(() => {
    async function fetchCompanyData() {
      if (!id) return;
      try {
        setLoadingCompany(true);
        const data = await getCompany(id);
        setCompany(data);
      } catch (err) {
        setError('Failed to load company details.');
        console.error(err);
      } finally {
        setLoadingCompany(false);
      }
    }
    fetchCompanyData();
  }, [id]);

  // Fetch Contacts
  const fetchContactsData = useCallback(async () => {
    if (!id) return;
    try {
      setLoadingContacts(true);
      const res = await getContacts({
        company: id,
        page,
        page_size: pageSize
      });
      setContactsData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingContacts(false);
    }
  }, [id, page, pageSize]);

  useEffect(() => {
    fetchContactsData();
  }, [fetchContactsData]);

  const handleDeleteContact = async (c: Contact) => {
    if (!window.confirm(`Are you sure you want to delete ${c.full_name}?`)) return;
    try {
      await deleteContact(c.id);
      fetchContactsData();
    } catch (err) {
      alert("Failed to delete contact.");
    }
  };

  const handleModalClose = (wasSaved: boolean) => {
    setIsModalOpen(false);
    if (wasSaved) fetchContactsData();
  };

  if (error) {
    return <div className="detailContainer"><div className="modalError">{error}</div></div>;
  }

  if (loadingCompany || !company) {
    return (
      <div className="detailContainer" style={{display: 'flex', justifyContent: 'center', marginTop: '100px'}}>
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="detailContainer">
      <Link to="/companies" className="backLink">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to Companies
      </Link>

      <section className="companyHeaderCard">
        {company.logo_url ? (
          <img src={company.logo_url} alt={company.name} className="detailLogo" />
        ) : (
          <div className="detailLogoPlaceholder">
            {company.name.charAt(0).toUpperCase()}
          </div>
        )}
        
        <div className="companyInfoBlock">
          <h1>{company.name}</h1>
          <div className="metaTags">
            <span className="metaBadge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
              </svg>
              {company.industry || 'No Industry'}
            </span>
            <span className="metaBadge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              {company.country || 'No Country'}
            </span>
            <span className="metaBadge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
              Added {company.created_at ? new Date(company.created_at).toLocaleDateString() : 'Unknown'}
            </span>
          </div>
        </div>
      </section>

      <section className="contactsSection">
        <div className="sectionHeader">
          <div>
            <h2>Contact Directory</h2>
            <p>Manage people who work at {company.name}</p>
          </div>
          <button 
            className="primaryBtn" 
            onClick={() => { setSelectedContact(undefined); setIsModalOpen(true); }}
          >
             <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Add Contact
          </button>
        </div>

        {loadingContacts ? (
          <div className="loadingState">
            <div className="spinner"></div>
          </div>
        ) : contactsData?.results.length === 0 ? (
          <div className="emptyState" style={{background: 'white', borderRadius: '12px', border: '1px solid #e2e8f0'}}>
            <svg style={{margin: '0 auto 16px', color: '#94a3b8'}} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            No contacts listed. Click "Add Contact" to get started!
          </div>
        ) : (
          <div className="contactGrid">
            {contactsData?.results.map(contact => (
              <div className="contactCard" key={contact.id}>
                
                <div className="contactActions">
                  {canEdit && (
                    <button className="cardIconBtn" title="Edit" onClick={() => { setSelectedContact(contact); setIsModalOpen(true); }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                      </svg>
                    </button>
                  )}
                  {canDelete && (
                    <button className="cardIconBtn delete" title="Delete" onClick={() => handleDeleteContact(contact)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                    </button>
                  )}
                </div>

                <div className="contactHeader">
                  <div>
                    <h3 className="contactName">{contact.full_name}</h3>
                    <p className="contactRole">{contact.role || 'Team Member'}</p>
                  </div>
                </div>

                <div className="contactDataList">
                  <div className="contactDataRow">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                      <polyline points="22,6 12,13 2,6"></polyline>
                    </svg>
                    {contact.email}
                  </div>
                  {contact.phone && (
                    <div className="contactDataRow">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                      </svg>
                      {contact.phone}
                    </div>
                  )}
                </div>

              </div>
            ))}
          </div>
        )}

        {contactsData && contactsData.total_pages > 1 && (
          <div style={{display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '32px'}}>
            <button 
              className="primaryBtn" style={{background: 'white', color: '#0f172a', border: '1px solid #cbd5e1'}}
              disabled={page === 1} onClick={() => setPage(p => p - 1)}
            >Previous</button>
            <button 
              className="primaryBtn" style={{background: 'white', color: '#0f172a', border: '1px solid #cbd5e1'}}
              disabled={page === contactsData.total_pages} onClick={() => setPage(p => p + 1)}
            >Next</button>
          </div>
        )}
      </section>

      {isModalOpen && id && (
        <ContactModal 
          isOpen={isModalOpen}
          companyId={id}
          contact={selectedContact}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
