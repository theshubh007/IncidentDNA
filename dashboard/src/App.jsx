import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider, useApp } from './hooks/useAppContext';
import Sidebar from './components/Sidebar';
import Toolbar from './components/Toolbar';
import Footer from './components/Footer';
import ToastContainer from './components/ToastContainer';
import SimulationModal from './components/SimulationModal';
import OverviewPage from './pages/OverviewPage';
import IncidentsPage from './pages/IncidentsPage';
import ReleasesPage from './pages/ReleasesPage';
import ServicesPage from './pages/ServicesPage';
import RunbooksPage from './pages/RunbooksPage';
import PostmortemsPage from './pages/PostmortemsPage';
import AuditPage from './pages/AuditPage';
import SettingsPage from './pages/SettingsPage';
import RepositoryPage from './pages/RepositoryPage';

function AppShell() {
  const { sidebarCollapsed } = useApp();

  return (
    <div className="app-shell">
      <Sidebar />
      <Toolbar />
      <main className={`app-main${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
        <div className="app-content">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/releases" element={<ReleasesPage />} />
            <Route path="/services" element={<ServicesPage />} />
            <Route path="/runbooks" element={<RunbooksPage />} />
            <Route path="/postmortems" element={<PostmortemsPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/repository" element={<RepositoryPage />} />
          </Routes>
        </div>
      </main>
      <Footer />
      <ToastContainer />
      <SimulationModal />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppShell />
      </AppProvider>
    </BrowserRouter>
  );
}
