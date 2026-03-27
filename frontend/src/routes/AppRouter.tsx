import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/ProtectedRoute';
import MainLayout from '../components/MainLayout';
import Login from '../pages/Login';
import Dashboard from '../pages/Dashboard';
import Companies from '../pages/Companies';
import CompanyDetail from '../pages/CompanyDetail';
import Contacts from '../pages/Contacts';
import ActivityLogs from '../pages/ActivityLogs';

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/companies" element={<Companies />} />
            <Route path="/companies/:id" element={<CompanyDetail />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/activity-logs" element={<ActivityLogs />} />
            {/* Default protected route */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
