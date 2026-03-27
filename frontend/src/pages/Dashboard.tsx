import { useAuthStore } from '../store/authStore';
import './Dashboard.css';

export default function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  // Fallbacks in case user profile isn't fully loaded yet
  const fullName = user?.full_name || 'User';
  const role = user?.role || 'member';
  const orgName = user?.organization?.name || 'Organization';
  const orgPlan = user?.organization?.plan || 'basic';

  return (
    <div className="dashboardContainer">
      <header className="dashboardHeader">
        <h1>
          {orgName} <span className="orgBadge">{orgPlan} Plan</span>
        </h1>
        <div className="userInfo">
          <span className="userRole">{role.charAt(0).toUpperCase() + role.slice(1)}</span>
          <button className="logoutBtn" onClick={() => logout()}>
            Sign out
          </button>
        </div>
      </header>

      <main className="dashboardContent">
        <section className="welcomeSection">
          <h2>Welcome back, {fullName}</h2>
          <p>Here's an overview of your organization's activity.</p>
        </section>

        <section className="statsGrid">
          <div className="statCard">
            <div className="statHeader">
              <div className="statIcon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
              Total Customers
            </div>
            <p className="statValue">1,248</p>
            <div className="statTrend">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
                <polyline points="16 7 22 7 22 13"></polyline>
              </svg>
              +12% this month
            </div>
          </div>

          <div className="statCard">
            <div className="statHeader">
              <div className="statIcon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                </svg>
              </div>
              Active Projects
            </div>
            <p className="statValue">42</p>
            <div className="statTrend">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
                <polyline points="16 7 22 7 22 13"></polyline>
              </svg>
              +4 this week
            </div>
          </div>

          <div className="statCard">
            <div className="statHeader">
              <div className="statIcon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="1" x2="12" y2="23"></line>
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
              </div>
              Monthly Revenue
            </div>
            <p className="statValue">$34,500</p>
            <div className="statTrend">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
                <polyline points="16 7 22 7 22 13"></polyline>
              </svg>
              +8.1% vs last month
            </div>
          </div>
        </section>

        <section className="orgDetailsCard">
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#1e293b' }}>Profile Details</h3>
          <div className="orgDetailsGrid">
            <div className="detailItem">
              <span className="detailLabel">Full Name</span>
              <span className="detailValue">{fullName}</span>
            </div>
            <div className="detailItem">
              <span className="detailLabel">Email Address</span>
              <span className="detailValue">{user?.email || 'email@example.com'}</span>
            </div>
            <div className="detailItem">
              <span className="detailLabel">Role</span>
              <span className="detailValue" style={{ textTransform: 'capitalize' }}>{role}</span>
            </div>
            <div className="detailItem">
              <span className="detailLabel">Member Since</span>
              <span className="detailValue">
                {user?.date_joined ? new Date(user.date_joined).toLocaleDateString() : 'Unknown'}
              </span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
