import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";

import LandingPage from "./routes/LandingPage";
import LoginPage from "./routes/LoginPage";
import SignupPage from "./routes/SignupPage";
import ForgotPasswordPage from "./routes/ForgotPasswordPage";
import OnboardingPage from "./routes/OnboardingPage";
import ProductPage from "./routes/ProductPage";
import FeatureEvidenceGraphPage from "./routes/FeatureEvidenceGraphPage";
import FeatureAIInvestigationsPage from "./routes/FeatureAIInvestigationsPage";

import OverviewPage from "./routes/OverviewPage";
import SourcesPage from "./routes/SourcesPage";
import MappingReviewPage from "./routes/MappingReviewPage";
import IntegrationsPage from "./routes/IntegrationsPage";
import CampaignsPage from "./routes/CampaignsPage";
import CampaignDetailPage from "./routes/CampaignDetailPage";
import CampaignComparisonPage from "./routes/CampaignComparisonPage";
import InvestigationsPage from "./routes/InvestigationsPage";
import EvidenceGraphPage from "./routes/EvidenceGraphPage";
import ContentStudioPage from "./routes/ContentStudioPage";
import RecommendationsPage from "./routes/RecommendationsPage";
import ExperimentsPage from "./routes/ExperimentsPage";
import ReportsPage from "./routes/ReportsPage";
import DataQualityPage from "./routes/DataQualityPage";
import EvaluationPage from "./routes/EvaluationPage";
import ModelSettingsPage from "./routes/ModelSettingsPage";
import SettingsPage from "./routes/SettingsPage";
import ActivityLogPage from "./routes/ActivityLogPage";

function Protected({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/product" element={<ProductPage />} />
          <Route path="/features/evidence-graph" element={<FeatureEvidenceGraphPage />} />
          <Route path="/features/ai-investigations" element={<FeatureAIInvestigationsPage />} />

          {/* Authenticated */}
          <Route path="/app/overview" element={<Protected><OverviewPage /></Protected>} />
          <Route path="/app/sources" element={<Protected><SourcesPage /></Protected>} />
          <Route path="/app/mapping-review" element={<Protected><MappingReviewPage /></Protected>} />
          <Route path="/app/integrations" element={<Protected><IntegrationsPage /></Protected>} />
          <Route path="/app/campaigns" element={<Protected><CampaignsPage /></Protected>} />
          <Route path="/app/campaigns/:campaignId" element={<Protected><CampaignDetailPage /></Protected>} />
          <Route path="/app/campaign-comparison" element={<Protected><CampaignComparisonPage /></Protected>} />
          <Route path="/app/investigations" element={<Protected><InvestigationsPage /></Protected>} />
          <Route path="/app/evidence-graph" element={<Protected><EvidenceGraphPage /></Protected>} />
          <Route path="/app/content-studio" element={<Protected><ContentStudioPage /></Protected>} />
          <Route path="/app/recommendations" element={<Protected><RecommendationsPage /></Protected>} />
          <Route path="/app/experiments" element={<Protected><ExperimentsPage /></Protected>} />
          <Route path="/app/reports" element={<Protected><ReportsPage /></Protected>} />
          <Route path="/app/data-quality" element={<Protected><DataQualityPage /></Protected>} />
          <Route path="/app/evaluation" element={<Protected><EvaluationPage /></Protected>} />
          <Route path="/app/settings/model" element={<Protected><ModelSettingsPage /></Protected>} />
          <Route path="/app/settings" element={<Protected><SettingsPage /></Protected>} />
          <Route path="/app/activity" element={<Protected><ActivityLogPage /></Protected>} />

          {/* Fallback */}
          <Route path="*" element={<LandingPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
