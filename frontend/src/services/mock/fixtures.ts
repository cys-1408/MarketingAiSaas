import type {
  Campaign, DataSource, Integration, MappingCandidate, Recommendation,
  Experiment, EvidenceRecord, GNode, GEdge,
} from "../../types";

export const DEMO_MODE = true;

export const currentUser = {
  id: "u1", name: "Avery Chen", email: "avery@northfield.io",
  role: "Marketing Manager", avatarInitials: "AC",
};

export const currentWorkspace = { id: "w1", name: "Northfield Growth Team", plan: "Team", memberCount: 6 };

export const dataSources: DataSource[] = [
  { id: "s1", name: "paid_social_q3.csv", type: "csv", category: "Ad Platform Export", records: 18234, status: "ready", updatedAt: "2 hours ago", version: 3 },
  { id: "s2", name: "crm_contacts_export.xlsx", type: "xlsx", category: "CRM", records: 9120, status: "awaiting_review", updatedAt: "4 hours ago", version: 1 },
  { id: "s3", name: "customer_interviews_sept.docx", type: "docx", category: "Qualitative Feedback", records: 42, status: "indexing", updatedAt: "12 min ago", version: 1 },
  { id: "s4", name: "email_campaign_results.csv", type: "csv", category: "Email Marketing", records: 5400, status: "validating", updatedAt: "1 day ago", version: 2 },
  { id: "s5", name: "product_launch_brief.pdf", type: "pdf", category: "Product Facts", records: 12, status: "ready", updatedAt: "3 days ago", version: 1 },
  { id: "s6", name: "support_tickets_export.json", type: "json", category: "Customer Support", records: 2310, status: "retryable_failure", updatedAt: "5 hours ago", version: 1 },
];

export const mappingCandidates: MappingCandidate[] = [
  {
    id: "m1", sourceFile: "crm_contacts_export.xlsx", sheet: "Contacts", column: "lead_src",
    sampleValues: ["paid-social", "organic_search", "ref"], proposedField: "acquisition_channel",
    alternatives: ["lead_source_raw", "utm_source"], confidence: "medium",
    reason: "Column values are abbreviated and overlap with two canonical fields.",
    impact: "Affects channel attribution on 9,120 contact records.", resolved: false,
  },
  {
    id: "m2", sourceFile: "crm_contacts_export.xlsx", sheet: "Contacts", column: "deal_stg",
    sampleValues: ["SQL", "Opp", "Closed-Won"], proposedField: "pipeline_stage",
    alternatives: ["lifecycle_stage"], confidence: "high",
    reason: "High-confidence match but stage names are non-standard.",
    impact: "Affects conversion funnel accuracy.", resolved: false,
  },
  {
    id: "m3", sourceFile: "email_campaign_results.csv", sheet: "Sheet1", column: "ctr_pct",
    sampleValues: ["2.4", "0.031", "4.1%"], proposedField: "click_through_rate",
    alternatives: ["engagement_rate"], confidence: "low",
    reason: "Mixed formatting (percentage vs decimal) creates ambiguity.",
    impact: "Could misstate CTR by an order of magnitude if unresolved.", resolved: false,
  },
];

export const integrations: Integration[] = [
  { id: "i1", name: "Google Analytics 4", category: "web_analytics", description: "Website traffic, sessions, and on-site conversion events.", status: "connected", lastSync: "18 min ago" },
  { id: "i2", name: "Meta Ads", category: "advertising", description: "Campaign spend, reach, and placement performance.", status: "connected", lastSync: "1 hour ago" },
  { id: "i3", name: "Google Ads", category: "advertising", description: "Search and display campaign metrics.", status: "error" },
  { id: "i4", name: "HubSpot", category: "crm", description: "Contacts, deals, and lifecycle stages.", status: "not_connected" },
  { id: "i5", name: "Klaviyo", category: "email", description: "Email campaign performance and flows.", status: "syncing", lastSync: "Syncing now" },
  { id: "i6", name: "Salesforce", category: "crm", description: "Opportunity and account-level revenue data.", status: "not_connected" },
];

export const campaigns: Campaign[] = [
  { id: "c1", name: "Autumn Acquisition Push", status: "active", channel: "Paid Social", audience: "New Prospects 25-44", product: "Core Platform", period: "Sep 1 – Sep 30", spend: 24500, impressions: 1820000, clicks: 31400, conversions: 612, revenue: 91800 },
  { id: "c2", name: "Retention Win-back", status: "active", channel: "Email", audience: "Lapsed Customers", product: "Core Platform", period: "Sep 10 – Oct 10", spend: 3200, impressions: 98000, clicks: 6100, conversions: 340, revenue: 48900 },
  { id: "c3", name: "Search Brand Defense", status: "paused", channel: "Paid Search", audience: "Branded Intent", product: "Core Platform", period: "Aug 1 – Sep 15", spend: 11200, impressions: 420000, clicks: 18900, conversions: 505, revenue: 72300 },
  { id: "c4", name: "Product Launch — Studio", status: "completed", channel: "Paid Social", audience: "Existing Customers", product: "Studio Add-on", period: "Jul 1 – Jul 31", spend: 18800, impressions: 1390000, clicks: 22100, conversions: 288, revenue: 39600 },
  { id: "c5", name: "Q4 Pipeline Builder", status: "draft", channel: "Paid Search", audience: "Mid-Market B2B", product: "Core Platform", period: "Oct 1 – Dec 31", spend: 0, impressions: 0, clicks: 0, conversions: 0, revenue: 0 },
];

export const evidenceRecords: EvidenceRecord[] = [
  { id: "e1", sourceName: "paid_social_q3.csv", sourceVersion: 3, dateRange: "Sep 1 – Sep 30", excerpt: "CTR for Autumn Acquisition Push averaged 1.73%, above the 90-day account median of 1.1%.", evidenceType: "Metric observation", relatedCampaign: "c1" },
  { id: "e2", sourceName: "customer_interviews_sept.docx", sourceVersion: 1, dateRange: "Sep 5 – Sep 22", excerpt: "6 of 14 interviewed prospects cited unclear pricing as a reason for not completing signup.", evidenceType: "Qualitative feedback", relatedCampaign: "c1" },
  { id: "e3", sourceName: "support_tickets_export.json", sourceVersion: 1, dateRange: "Aug 15 – Sep 30", excerpt: "Objection tag 'price_confusion' appears on 11% of pre-sale tickets, up from 6% last quarter.", evidenceType: "Support signal", relatedCampaign: "c1" },
];

export const recommendations: Recommendation[] = [
  {
    id: "r1", action: "Add a clear pricing summary to the Autumn Acquisition landing page.",
    scope: "Campaign: Autumn Acquisition Push", observedFacts: ["Click-to-signup rate is 1.9%, below the 3.4% campaign-type benchmark.", "11% of pre-sale support tickets reference pricing confusion."],
    interpretation: "Visitors are clicking ads successfully but dropping off before completing signup, and support data points to pricing clarity as a contributing factor.",
    hypothesis: "A clearer pricing summary above the fold may reduce drop-off at the signup step.",
    supportingEvidence: ["e2", "e3"], contradictoryEvidence: [],
    primaryMetric: "Click-to-signup rate", risks: ["Simplified pricing may omit plan nuances relevant to enterprise buyers."],
    missingData: ["Scroll-depth analytics for the landing page are not yet connected."],
    status: "under_review",
  },
  {
    id: "r2", action: "Reallocate 15% of Search Brand Defense budget to Retention Win-back.",
    scope: "Cross-campaign", observedFacts: ["Win-back campaign shows a 5.6x ROAS versus 2.1x for Brand Defense over the trailing 30 days."],
    interpretation: "Retention spend is currently outperforming defensive brand search on a return basis.",
    hypothesis: "Incremental budget in the win-back channel may sustain similar returns, though diminishing returns are untested.",
    supportingEvidence: ["e1"], contradictoryEvidence: ["Brand search traffic also suppresses competitor bidding, a value not captured in ROAS alone."],
    primaryMetric: "Return on ad spend", risks: ["Reduced brand defense could cede search terms to competitors."],
    missingData: ["Competitor bid pressure data is not connected."],
    status: "new",
  },
];

export const experiments: Experiment[] = [
  {
    id: "x1", name: "Pricing clarity landing page test", hypothesis: "A simplified pricing block above the fold increases click-to-signup rate by a measurable margin.",
    control: "Current landing page", variant: "Landing page with pricing summary module",
    primaryMetric: "Click-to-signup rate", guardrailMetrics: ["Average order value", "Support ticket volume"],
    status: "under_review", duration: "14 days (est.)", relatedRecommendation: "r1",
  },
  {
    id: "x2", name: "Win-back subject line test", hypothesis: "A benefit-led subject line outperforms a discount-led subject line for lapsed customers.",
    control: "Discount-led subject line", variant: "Benefit-led subject line",
    primaryMetric: "Open rate", guardrailMetrics: ["Unsubscribe rate"],
    status: "running", duration: "7 days",
  },
];

export const graphNodes: GNode[] = [
  { id: "n1", label: "Autumn Acquisition Push", type: "campaign", x: 120, y: 200 },
  { id: "n2", label: "Paid Social", type: "channel", x: 320, y: 90 },
  { id: "n3", label: "CTR 1.73%", type: "metric", x: 320, y: 310 },
  { id: "n4", label: "Pricing confusion", type: "objection", x: 540, y: 200 },
  { id: "n5", label: "Core Platform", type: "product", x: 540, y: 380 },
  { id: "n6", label: "Add pricing summary", type: "recommendation", x: 760, y: 200 },
  { id: "n7", label: "Pricing clarity test", type: "experiment", x: 960, y: 200 },
  { id: "n8", label: "customer_interviews_sept.docx", type: "source", x: 540, y: 60 },
];

export const graphEdges: GEdge[] = [
  { id: "ge1", source: "n1", target: "n2", relation: "runs on", observed: true },
  { id: "ge2", source: "n1", target: "n3", relation: "measured by", observed: true },
  { id: "ge3", source: "n1", target: "n4", relation: "associated with", observed: true },
  { id: "ge4", source: "n4", target: "n8", relation: "sourced from", observed: true },
  { id: "ge5", source: "n4", target: "n5", relation: "relates to", observed: false },
  { id: "ge6", source: "n4", target: "n6", relation: "informs", observed: false },
  { id: "ge7", source: "n6", target: "n7", relation: "tested by", observed: true },
];
