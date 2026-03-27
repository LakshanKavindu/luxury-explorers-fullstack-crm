import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getCompanies, deleteCompany } from '../api/companyApi';
import type { Company, PaginatedResponse } from '../types/crm';

import './Companies.css';
import CompanyModal from '../components/CompanyModal';

export default function Companies() {
  const user = useAuthStore((state) => state.user);

  // State
  const [data, setData] = useState<PaginatedResponse<Company> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | undefined>(undefined);

  // Permissions
  const canEdit = user?.role === 'admin' || user?.role === 'manager';
  const canDelete = user?.role === 'admin';

  const fetchCompanies = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const res = await getCompanies({
        search: searchTerm,
        page,
        page_size: pageSize
      });
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch companies. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, page, pageSize]);

  // Initial fetch and distinct updates
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchCompanies();
    }, 300); // debounce search
    return () => clearTimeout(delayDebounceFn);
  }, [fetchCompanies]);

  const handleDelete = async (company: Company) => {
    if (!window.confirm(`Are you sure you want to delete ${company.name}?`)) return;

    try {
      await deleteCompany(company.id);
      if (data?.results.length === 1 && page > 1) {
        setPage(page - 1);
      } else {
        fetchCompanies();
      }
    } catch (err) {
      alert('Failed to delete company.');
    }
  };

  const openCreateModal = () => {
    setSelectedCompany(undefined);
    setIsModalOpen(true);
  };

  const openEditModal = (company: Company) => {
    setSelectedCompany(company);
    setIsModalOpen(true);
  };

  const handleModalClose = (wasSaved: boolean) => {
    setIsModalOpen(false);
    if (wasSaved) {
      fetchCompanies();
    }
  };

  return (
    <div className="companiesContainer">
      <div className="pageHeader">
        <div className="pageTitle">
          <h1>Companies</h1>
          <p>Manage your client organizations and partnerships.</p>
        </div>

        <div className="controlsRow">
          <input
            type="text"
            placeholder="Search by name, industry, or country..."
            className="searchInput"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1); // Reset to page 1 on search
            }}
          />
          <button className="primaryBtn" onClick={openCreateModal}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Add Company
          </button>
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
          <table className="companyTable">
            <thead>
              <tr>
                <th>Company</th>
                <th>Industry</th>
                <th>Country</th>
                <th>Created</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.results.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="emptyState">No companies found. Try a different search term or add a new one!</div>
                  </td>
                </tr>
              ) : (
                data?.results.map(company => (
                  <tr key={company.id}>
                    <td>
                      <div className="companyCell">
                        {company.logo_url ? (
                          <img src={company.logo_url} alt={`${company.name} logo`} className="companyLogo" />
                        ) : (
                          <div className="companyLogoPlaceholder">{company.name.charAt(0).toUpperCase()}</div>
                        )}
                        <Link to={`/companies/${company.id}`} className="companyName" style={{ textDecoration: 'none' }}>
                          {company.name}
                        </Link>
                      </div>
                    </td>
                    <td>{company.industry || '-'}</td>
                    <td>{company.country || '-'}</td>
                    <td>{company.created_at ? new Date(company.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                      <div className="actionsCell">
                        {canEdit && (
                          <button className="iconBtn" onClick={() => openEditModal(company)} title="Edit">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                          </button>
                        )}
                        {canDelete && (
                          <button className="iconBtn delete" onClick={() => handleDelete(company)} title="Delete">
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

          {/* Pagination Controls */}
          {data && data.total_pages > 1 && (
            <div className="pagination">
              <div className="pageInfo">
                Showing {Math.min((page - 1) * pageSize + 1, data.count)} to {Math.min(page * pageSize, data.count)} of {data.count} entries
              </div>
              <div className="pageControls">
                <button
                  className="pageBtn"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <button
                  className="pageBtn"
                  disabled={page === data.total_pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {isModalOpen && (
        <CompanyModal
          isOpen={isModalOpen}
          company={selectedCompany}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
