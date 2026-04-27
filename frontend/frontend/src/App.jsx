import { Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import CreateAccountPage from './pages/CreateAccountPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import AiMatchmakingPage from './pages/AiMatchmakingPage';
import MyContractsPage from './pages/MyContractsPage';
import ProfilePage from './pages/ProfilePage';
import NotificationsPage from './pages/NotificationsPage';
import ContractDetailPage from './pages/ContractDetailPage';
import RfpGeneratorPage from './pages/RfpGeneratorPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/create-account" element={<CreateAccountPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/ai-matchmaking" element={<AiMatchmakingPage />} />
      <Route path="/my-contracts" element={<MyContractsPage />} />
      <Route path="/contracts/:contractId" element={<ContractDetailPage />} />
      <Route path="/rfp-generator" element={<RfpGeneratorPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/notifications" element={<NotificationsPage />} />
    </Routes>
  );
}

export default App;
