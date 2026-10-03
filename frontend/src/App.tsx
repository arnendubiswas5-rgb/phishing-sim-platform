import { Navigate, Route, Routes } from "react-router-dom";
import { AuthGuard } from "./components/AuthGuard";
import { DashboardLayout } from "./components/DashboardLayout";
import { CampaignsPage } from "./pages/CampaignsPage";
import { CampaignWizard } from "./pages/CampaignWizard";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { PageEditorPage } from "./pages/PageEditorPage";
import { PagesListPage } from "./pages/PagesListPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { ReportsPage } from "./pages/ReportsPage";
import { TermsPage } from "./pages/TermsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TargetsPage } from "./pages/TargetsPage";
import { TemplatesPage } from "./pages/TemplatesPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/terms" element={<TermsPage />} />

      {/* Every route below is gated by AuthGuard and framed by DashboardLayout. */}
      <Route element={<AuthGuard />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/campaigns/new" element={<CampaignWizard />} />
          <Route path="/targets" element={<TargetsPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/pages" element={<PagesListPage />} />
          <Route path="/pages/new" element={<PageEditorPage />} />
          <Route path="/pages/:id" element={<PageEditorPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
