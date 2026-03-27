import { Outlet, NavLink } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './MainLayout.css';

export default function MainLayout() {
  const user = useAuthStore((state) => state.user);
  
  const getInitials = (name?: string) => {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  return (
    <div className="layoutContainer">
      <aside className="sidebar">
        <div className="sidebarHeader">
          <h2>Luxury CRM</h2>
        </div>
        <nav className="sidebarNav">
          <NavLink 
            to="/dashboard" 
            className={({ isActive }) => `navLink ${isActive ? 'active' : ''}`}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="9"></rect>
              <rect x="14" y="3" width="7" height="5"></rect>
              <rect x="14" y="12" width="7" height="9"></rect>
              <rect x="3" y="16" width="7" height="5"></rect>
            </svg>
            Dashboard
          </NavLink>
          <NavLink 
            to="/companies" 
            className={({ isActive }) => `navLink ${isActive ? 'active' : ''}`}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18"></path>
              <path d="M9 8h1"></path>
              <path d="M9 12h1"></path>
              <path d="M9 16h1"></path>
              <path d="M14 8h1"></path>
              <path d="M14 12h1"></path>
              <path d="M14 16h1"></path>
              <path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"></path>
            </svg>
            Companies
          </NavLink>
        </nav>
        <div className="sidebarFooter">
          <div className="currentUserInfo">
            <div className="avatar">{getInitials(user?.full_name)}</div>
            <div className="currentUserName">
              <span>{user?.full_name || 'User'}</span>
              <span>{user?.role || 'member'}</span>
            </div>
          </div>
        </div>
      </aside>
      
      <main className="mainContent">
        <Outlet />
      </main>
    </div>
  );
}
