import { useState, useEffect, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getLogs } from '../api/auditApi';
import type { ActivityLog, PaginatedResponse } from '../types/crm';
import './ActivityLogs.css';

export default function ActivityLogs() {
  const user = useAuthStore((state) => state.user);
  
  // State
  const [data, setData] = useState<PaginatedResponse<ActivityLog> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Hard block standard roles from accessing this page entirely.
  // In a robust app, use layout router shielding, but Component level mapping works well here.
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const res = await getLogs({
        search: searchTerm,
        page,
        page_size: pageSize
      });
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch activity logs. Ensure your permissions are correct.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, page, pageSize]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchLogs();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [fetchLogs]);

  return (
    <div className="logsContainer">
      <div style={{marginBottom: '32px'}}>
        <h1 style={{fontSize: '28px', fontWeight: 700, margin: '0 0 8px 0'}}>Activity Log</h1>
        <p style={{color: '#64748b', margin: 0}}>Audit trail describing all creations, revisions, and deletions in the organization.</p>
      </div>

      <div className="logSearch">
        <input 
          type="text" 
          placeholder="Search logs by action, object, or user..." 
          className="logSearchInput"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {error ? (
        <div style={{ color: '#ef4444', padding: '20px', background: '#fef2f2', borderRadius: '8px' }}>
          {error}
        </div>
      ) : loading && !data ? (
        <div className="logsLoading">
          <div className="spinner"></div>
        </div>
      ) : (
        <div className="logsTableCard">
          <table className="logsTable">
            <thead>
              <tr>
                <th>Action</th>
                <th>Resource</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {data?.results.length === 0 ? (
                <tr>
                  <td colSpan={3}>
                    <div style={{padding: '48px', textAlign: 'center', color: '#64748b'}}>
                      No activity logs match your search.
                    </div>
                  </td>
                </tr>
              ) : (
                data?.results.map(log => {
                  const badgeClass = log.action_display.toLowerCase();
                  
                  return (
                    <tr key={log.id}>
                      <td>
                        <span className={`actionBadge ${badgeClass}`}>
                          {log.action_display}
                        </span>
                        <div style={{fontSize: '13px', color: '#64748b', marginTop: '6px', fontWeight: 500}}>
                          by {log.user_display}
                        </div>
                      </td>
                      <td>
                        <div className="logMeta">
                          <p>{log.object_repr}</p>
                          <span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                            </svg>
                            {log.model_name}
                          </span>
                        </div>
                      </td>
                      <td style={{color: '#475569', fontSize: '13px'}}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
          
          {data && data.total_pages > 1 && (
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderTop: '1px solid #e2e8f0', background: 'white'}}>
              <div style={{fontSize: '14px', color: '#64748b'}}>
                Showing {Math.min((page - 1) * pageSize + 1, data.count)} to {Math.min(page * pageSize, data.count)} of {data.count} entries
              </div>
              <div style={{display: 'flex', gap: '8px'}}>
                <button 
                  style={{padding: '6px 16px', border: '1px solid #e2e8f0', background: 'white', borderRadius: '6px', fontSize: '14px', cursor: 'pointer', opacity: page === 1 ? 0.5 : 1}}
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </button>
                <button 
                  style={{padding: '6px 16px', border: '1px solid #e2e8f0', background: 'white', borderRadius: '6px', fontSize: '14px', cursor: 'pointer', opacity: page === data.total_pages ? 0.5 : 1}}
                  disabled={page === data.total_pages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
