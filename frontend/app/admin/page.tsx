"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  Clock3,
  Download,
  FileText,
  Gauge,
  Grid2X2,
  History,
  Package,
  Search,
  Send,
  Settings,
  Share2,
  Sparkles,
  Ticket,
  Truck,
  UserRound,
  X
} from "lucide-react";
import { apiGet, apiPost, ChatResponse, User } from "@/lib/api";
import type { EscalationQueue } from "@/lib/api";

type Message = {
  role: "user" | "agent";
  text: string;
  confidence?: string;
};

type Dashboard = {
  snapshot_time: string;
  summary: { open_tickets: number; high_severity: number; recurring_issue_groups: number };
  sla_risk: Array<Record<string, any>>;
  recurring_issues: Array<Record<string, any>>;
};

export type AdminView = "dashboard" | "insights" | "tickets" | "agreements";

const prompts = [
  "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.",
  "What support SLA applies to Northstar for a P1 incident?",
  "Escalate ticket TKT-501 because it is high severity and affects all Northstar shipment creation.",
  "Northstar says a SwiftShip order still shows BOOKED after driver pickup. What should support check?"
];

const anomalies = [
  {
    id: "ANM-8492",
    level: "critical",
    title: "Severe Weather Delay: Northeast Corridor",
    text: "Blizzard conditions detected in PA/NY affecting FedEx Hub. Prediction model indicates 85% probability of 48+ hour delays.",
    meta: "FedEx Ground / 12.4k parcels / Risk: $480k",
    action: "View Impact"
  },
  {
    id: "ANM-8491",
    level: "warning",
    title: "Unexpected Capacity Spike: Dallas Sort Facility",
    text: "Inbound volume at DFW node is exceeding 30-day moving average by 42%. Likely to cause localized bottleneck.",
    meta: "UPS Next Day Air / DFW-01 / +42% volume",
    action: "Investigate"
  },
  {
    id: "SYS-1024",
    level: "info",
    title: "Carrier API Latency Detected",
    text: "DHL Express tracking API response times are elevated. Fallback synchronization has been initiated.",
    meta: "DHL Express / API health / automated fallback",
    action: "Open"
  }
];

export default function AdminPage() {
  return <AdminConsole initialView="dashboard" />;
}

export function AdminConsole({ initialView = "dashboard" }: { initialView?: AdminView }) {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState("support_agent");
  const [view, setViewState] = useState<AdminView>(initialView);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      text: "Support Assistant Alpha is online. Ask about orders, contracts, policies, SLA risk, or escalations.",
      confidence: "high"
    }
  ]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [queue, setQueue] = useState<EscalationQueue>({ escalations: [], pending_actions: [] });
  const [toast, setToast] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    apiGet<{ users: User[] }>("/api/users").then((data) => setUsers(data.users.filter((user) => user.role !== "customer")));
  }, []);

  useEffect(() => {
    setViewState(initialView);
  }, [initialView]);

  useEffect(() => {
    void loadDashboard();
    void loadEscalations();
  }, [userId]);

  const activeUser = useMemo(() => users.find((user) => user.user_id === userId), [users, userId]);
  const totalTickets = dashboard?.summary.open_tickets ?? 0;
  const highSeverity = dashboard?.summary.high_severity ?? 0;
  const pendingAction = response?.pending_action as Record<string, any> | null | undefined;

  async function loadDashboard() {
    const data = await apiGet<Dashboard>("/api/dashboard", userId);
    setDashboard(data);
  }

  async function loadEscalations() {
    const data = await apiGet<EscalationQueue>("/api/escalations", userId);
    setQueue(data);
  }

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3200);
  }

  function setView(nextView: AdminView) {
    setViewState(nextView);
    router.push(nextView === "dashboard" ? "/admin" : `/admin/${nextView}`);
  }

  function runGlobalSearch(query: string) {
    const clean = query.trim();
    if (!clean) {
      notify("Enter a shipment, document, ticket, or policy question.");
      return;
    }
    const lower = clean.toLowerCase();
    if (lower.includes("agreement") || lower.includes("contract") || lower.includes("msa")) {
      setView("agreements");
      notify(`Opened agreement workspace for "${clean}".`);
      return;
    }
    if (lower.includes("insight") || lower.includes("risk") || lower.includes("anomaly")) {
      setView("insights");
      notify(`Filtered insights for "${clean}".`);
      return;
    }
    void send(clean);
  }

  function downloadTextFile(filename: string, content: string) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportReport() {
    downloadTextFile(
      "parcelpilot-insights-report.txt",
      [
        "ParcelPilot Proactive Insights Report",
        `Open tickets: ${dashboard?.summary.open_tickets ?? 0}`,
        `High severity: ${dashboard?.summary.high_severity ?? 0}`,
        `Escalations: ${queue.escalations.length}`,
        `Pending confirmations: ${queue.pending_actions.length}`,
        "",
        "Top anomalies:",
        ...anomalies.map((item) => `- ${item.level.toUpperCase()} ${item.id}: ${item.title}`)
      ].join("\n")
    );
    notify("Insights report downloaded.");
  }

  function shareAgreement() {
    const text = "Northstar Logistics Master Service Agreement - active agreement workspace";
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
    notify("Agreement share summary copied.");
  }

  function downloadAgreement() {
    downloadTextFile(
      "northstar-logistics-master-service-agreement.txt",
      "Northstar Logistics Master Service Agreement\n\nKey clauses:\n4.2 Service Level Commitments\n7.1 Liability Limits\n\nAI conflict analysis: 2 overrides found."
    );
    notify("Agreement export downloaded.");
  }

  function resetSession() {
    setMessages([{ role: "agent", text: "New support session started. Ask about orders, contracts, policies, SLA risk, or escalations.", confidence: "high" }]);
    setResponse(null);
    setInput("");
    notify("Support session reset.");
  }

  async function send(message: string) {
    const clean = message.trim();
    if (!clean) return;
    setView("tickets");
    setBusy(true);
    setMessages((current) => [
      ...current,
      { role: "user", text: clean },
      { role: "agent", text: "Executing authorized tools and scanning customer agreements..." }
    ]);
    const data = await apiPost<ChatResponse>("/api/chat", { user_id: userId, message: clean }, userId);
    setResponse(data);
    setMessages((current) => [
      ...current.slice(0, -1),
      { role: "agent", text: data.answer || data.error || "No response.", confidence: data.confidence }
    ]);
    await loadEscalations();
    setBusy(false);
  }

  async function refreshData() {
    const data = await apiPost<{ loaded?: string[] }>("/api/ingest", {}, userId);
    notify(`Data pack refreshed. Loaded ${(data.loaded || []).length} files.`);
    await loadDashboard();
    await loadEscalations();
  }

  async function confirmPending(actionId: string) {
    const result = await apiPost<{ executed?: Record<string, any>; detail?: string }>("/api/actions/confirm", { user_id: userId, action_id: actionId }, userId);
    notify(result.executed ? `Created escalation ${result.executed.id}` : result.detail || "Action failed");
    await loadEscalations();
  }

  async function verifyEscalation(escalationId: string) {
    const result = await apiPost<{ escalation?: Record<string, any>; detail?: string }>(`/api/escalations/${escalationId}/verify`, { user_id: userId, status: "verified" }, userId);
    notify(result.escalation ? `Verified ${result.escalation.id}` : result.detail || "Verification failed");
    await loadEscalations();
  }

  async function respondEscalation(escalationId: string) {
    const result = await apiPost<{ escalation?: Record<string, any>; detail?: string }>(
      `/api/escalations/${escalationId}/respond`,
      {
        user_id: userId,
        message: "A ParcelPilot specialist reviewed this case. We confirmed the account-specific policy and will follow the documented SLA/contract path for this shipment."
      },
      userId
    );
    notify(result.escalation ? `Response sent for ${result.escalation.id}` : result.detail || "Response failed");
    await loadEscalations();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = input;
    setInput("");
    await send(value);
  }

  return (
    <main className="pilotShell">
      <Sidebar view={view} setView={setView} activeUser={activeUser} />

      <section className="pilotWorkspace">
        <Topbar
          userId={userId}
          users={users}
          setUserId={setUserId}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearch={runGlobalSearch}
          refreshData={refreshData}
          notificationsOpen={notificationsOpen}
          settingsOpen={settingsOpen}
          toggleNotifications={() => {
            setNotificationsOpen((open) => !open);
            setSettingsOpen(false);
          }}
          toggleSettings={() => {
            setSettingsOpen((open) => !open);
            setNotificationsOpen(false);
          }}
          queue={queue}
        />

        {view === "dashboard" && (
          <DashboardScreen totalTickets={totalTickets} highSeverity={highSeverity} dashboard={dashboard} setView={setView} />
        )}

        {view === "insights" && (
          <InsightsScreen
            dashboard={dashboard}
            queue={queue}
            confirmPending={confirmPending}
            verifyEscalation={verifyEscalation}
            respondEscalation={respondEscalation}
            exportReport={exportReport}
            generateSummary={() => void send("Generate an executive summary of current SLA risk, open escalations, and proactive anomalies.")}
            runAnomaly={(item) => void send(`Investigate ${item.id}: ${item.title}. Include impact, source evidence, and next action.`)}
            notify={notify}
          />
        )}

        {view === "tickets" && (
          <TicketsScreen
            messages={messages}
            response={response}
            input={input}
            setInput={setInput}
            submit={submit}
            busy={busy}
            prompts={prompts}
            send={send}
            pendingAction={pendingAction}
            confirmPending={confirmPending}
            notify={notify}
            resetSession={resetSession}
          />
        )}

        {view === "agreements" && <AgreementsScreen shareAgreement={shareAgreement} downloadAgreement={downloadAgreement} notify={notify} />}
      </section>

      {toast && <div className="nextToast">{toast}</div>}
    </main>
  );
}

function Sidebar({ view, activeUser }: { view: AdminView; setView: (view: AdminView) => void; activeUser?: User }) {
  const items: Array<{ id: AdminView; label: string; icon: typeof Grid2X2 }> = [
    { id: "dashboard", label: "Dashboard", icon: Grid2X2 },
    { id: "insights", label: "Insights", icon: BarChart3 },
    { id: "tickets", label: "Tickets", icon: Ticket },
    { id: "agreements", label: "Agreements", icon: FileText }
  ];

  return (
    <aside className="pilotSidebar">
      <div className="pilotBrand">
        <div className="miniMark">PP</div>
        <strong>ParcelPilot</strong>
      </div>

      <nav className="pilotNav">
        {items.map((item) => {
          const Icon = item.icon;
          const href = item.id === "dashboard" ? "/admin" : `/admin/${item.id}`;
          return (
            <Link key={item.id} href={href} className={view === item.id ? "active" : ""}>
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="adminIdentity">
        <div className="avatar">LA</div>
        <div>
          <strong>{activeUser?.display_name || "Logistics Admin"}</strong>
          <span>Enterprise Tier</span>
        </div>
      </div>
    </aside>
  );
}

function Topbar({
  userId,
  users,
  setUserId,
  searchQuery,
  setSearchQuery,
  onSearch,
  refreshData,
  notificationsOpen,
  settingsOpen,
  toggleNotifications,
  toggleSettings,
  queue
}: {
  userId: string;
  users: User[];
  setUserId: (value: string) => void;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  onSearch: (query: string) => void;
  refreshData: () => void;
  notificationsOpen: boolean;
  settingsOpen: boolean;
  toggleNotifications: () => void;
  toggleSettings: () => void;
  queue: EscalationQueue;
}) {
  return (
    <header className="pilotTopbar">
      <form className="pilotSearch" onSubmit={(event) => { event.preventDefault(); onSearch(searchQuery); }}>
        <Search size={20} />
        <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search shipments or documents..." />
      </form>
      <select className="identitySelect" value={userId} onChange={(event) => setUserId(event.target.value)}>
        {users.length === 0 && <option value={userId}>Loading admin identities...</option>}
        {users.map((user) => (
          <option key={user.user_id} value={user.user_id}>
            {user.display_name} / {user.role}
          </option>
        ))}
      </select>
      <button className="iconOnly notificationButton" onClick={toggleNotifications} aria-label="Notifications">
        <Bell size={20} />
        {(queue.pending_actions.length + queue.escalations.filter((item) => item.status !== "verified").length) > 0 && <span />}
      </button>
      <button className="iconOnly" onClick={toggleSettings} aria-label="Settings"><Settings size={20} /></button>
      {notificationsOpen && <NotificationsPanel queue={queue} refreshData={refreshData} />}
      {settingsOpen && <SettingsPanel />}
    </header>
  );
}

function DashboardScreen({ totalTickets, highSeverity, dashboard, setView }: { totalTickets: number; highSeverity: number; dashboard: Dashboard | null; setView: (view: AdminView) => void }) {
  return (
    <section className="pilotPage dashboardPage">
      <div className="metricCards">
        <MetricCard label="Total Active Tickets" value={String(totalTickets || 1248)} trend={`+${Math.max(highSeverity, 12)}%`} icon={<Ticket size={18} />} onClick={() => setView("tickets")} />
        <MetricCard label="Avg Resolution Time" value="14m" trend="-2m" icon={<Clock3 size={20} />} onClick={() => setView("insights")} />
        <MetricCard label="SLA Compliance" value="98.5%" trend="-0.0%" icon={<Gauge size={20} />} ring onClick={() => setView("insights")} />
      </div>

      <div className="dashboardGrid">
        <section className="pilotCard confidenceCard">
          <div className="cardHead">
            <div>
              <h2>AI Confidence Stream</h2>
              <p>Real-time automation accuracy across categories</p>
            </div>
            <TimeTabs />
          </div>
          <div className="confidenceViz">
            <svg viewBox="0 0 600 220" role="img" aria-label="AI confidence trend">
              <path d="M0 125 C90 108 152 120 226 141 C301 164 391 172 470 129 C520 102 555 70 600 25 L600 220 L0 220 Z" fill="#c7e8f1" />
              <path d="M0 125 C90 108 152 120 226 141 C301 164 391 172 470 129 C520 102 555 70 600 25" fill="none" stroke="#099484" strokeWidth="7" strokeLinecap="round" />
              <ellipse cx="150" cy="112" rx="17" ry="8" fill="#0b172a" />
              <ellipse cx="300" cy="148" rx="17" ry="8" fill="#0b172a" />
              <ellipse cx="455" cy="112" rx="17" ry="8" fill="#0b172a" />
            </svg>
          </div>
        </section>

        <section className="pilotCard volumeCard">
          <h2>Volume Trend</h2>
          <p>Ticket influx vs capacity</p>
          <div className="bars">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day, index) => <span key={day} style={{ height: `${42 + index * 12 - (index > 3 ? 35 : 0)}px` }}><i>{day}</i></span>)}</div>
        </section>
      </div>

      <section className="pilotCard activityCard">
        <div className="cardHead"><h2>Recent Activity</h2><Link href="/admin/insights">View All</Link></div>
        <ActivityRow icon={<Package size={16} />} title="Address Correction Applied" text="AI automatically resolved routing issue for tracking #TRK-8921" time="Just now" />
        <ActivityRow icon={<UserRound size={16} />} title="Customs Escalation" text="Assigned to Sarah Jenkins. AI confidence dropped below threshold." time="5m ago" danger />
        <ActivityRow icon={<Package size={16} />} title="Bulk ETA Update" text="Processed 450 weather delay notifications successfully." time="12m ago" />
      </section>
    </section>
  );
}

function InsightsScreen({
  dashboard,
  queue,
  confirmPending,
  verifyEscalation,
  respondEscalation,
  exportReport,
  generateSummary,
  runAnomaly,
  notify
}: {
  dashboard: Dashboard | null;
  queue: EscalationQueue;
  confirmPending: (id: string) => void;
  verifyEscalation: (id: string) => void;
  respondEscalation: (id: string) => void;
  exportReport: () => void;
  generateSummary: () => void;
  runAnomaly: (item: { id: string; level: string; title: string; text: string; meta: string; action: string }) => void;
  notify: (message: string) => void;
}) {
  const [insightSearch, setInsightSearch] = useState("");
  const [activeIssue, setActiveIssue] = useState("SLA Risk");
  const [viewed, setViewed] = useState(false);
  const filteredAnomalies = anomalies.filter((item) => {
    const haystack = `${item.title} ${item.text} ${item.meta}`.toLowerCase();
    return haystack.includes(insightSearch.toLowerCase());
  });

  return (
    <section className="pilotPage insightsPage">
      <div className="insightHero">
        <div>
          <h1>Proactive Insights</h1>
          <p>Real-time anomaly detection and predictive risk analysis across your logistics network.</p>
        </div>
        <div className="heroButtons"><button className="lightButton" onClick={exportReport}><Download size={16} />Export Report</button><button onClick={generateSummary}><Sparkles size={16} />Generate Summary</button></div>
      </div>

      <div className="insightsLayout">
        <aside className="filtersPanel">
          <h2>Filters</h2>
          <div className="pilotSearch compact"><Search size={15} /><input value={insightSearch} onChange={(event) => setInsightSearch(event.target.value)} placeholder="Search insights..." /></div>
          <FilterGroup title="Priority Level" values={["Critical (12)", "Warning (45)", "Info (128)"]} />
          <FilterGroup title="Carrier" values={["FedEx", "UPS", "DHL Express", "USPS"]} />
          <div className="issuePills">{["Weather Delay", "SLA Risk", "Customs Hold", "Capacity Spike", "Routing Error"].map((issue) => <button key={issue} className={activeIssue === issue ? "active" : ""} onClick={() => { setActiveIssue(issue); notify(`Insight filter set to ${issue}.`); }}>{issue}</button>)}</div>
        </aside>

        <section className="insightMain">
          <div className="riskStrip">
            <MetricMini title="Total Value At Risk" value="$1.24M" tone="danger" />
            <MetricMini title="Network SLA Success" value="94.2%" tone="success" />
            <MetricMini title="Volume Spikes" value={`${dashboard?.summary.recurring_issue_groups ?? 3} Regions`} tone="orange" />
          </div>

          <div className="sectionHead"><h2>Active Anomalies <span>{viewed ? "viewed" : "8 new"}</span></h2><button onClick={() => { setViewed(true); notify("All anomalies marked viewed."); }}>Mark all viewed</button></div>
          <div className="anomalyStack">{filteredAnomalies.map((item) => <AnomalyCard key={item.id} item={item} onAction={runAnomaly} />)}</div>

          <div className="sectionHead"><h2>Admin Escalation Review <span>{queue.escalations.length + queue.pending_actions.length} items</span></h2></div>
          <div className="reviewGrid">
            <ReviewColumn title="Pending Confirmation" empty="No pending state-changing actions.">
              {queue.pending_actions.map((item) => (
                <article className="reviewItem" key={item.id}>
                  <strong>{item.action_type}</strong>
                  <p>{item.summary}</p>
                  <button onClick={() => confirmPending(item.id)}>Confirm</button>
                </article>
              ))}
            </ReviewColumn>
            <ReviewColumn title="Escalated Tickets" empty="No escalations created yet.">
              {queue.escalations.map((item) => (
                <article className="reviewItem" key={item.id}>
                  <strong>{item.id} / {item.priority} / {item.status}</strong>
                  <p>{item.reason}</p>
                  {item.response && <p><b>Response:</b> {item.response}</p>}
                  {item.status !== "responded" && <button onClick={() => respondEscalation(item.id)}>Send Response</button>}
                  {item.status !== "verified" && <button onClick={() => verifyEscalation(item.id)}>Verify</button>}
                </article>
              ))}
            </ReviewColumn>
          </div>
        </section>
      </div>
    </section>
  );
}

function TicketsScreen({
  messages,
  response,
  input,
  setInput,
  submit,
  busy,
  prompts,
  send,
  pendingAction,
  confirmPending,
  notify,
  resetSession
}: {
  messages: Message[];
  response: ChatResponse | null;
  input: string;
  setInput: (value: string) => void;
  submit: (event: FormEvent<HTMLFormElement>) => void;
  busy: boolean;
  prompts: string[];
  send: (message: string) => void;
  pendingAction?: Record<string, any> | null;
  confirmPending: (id: string) => void;
  notify: (message: string) => void;
  resetSession: () => void;
}) {
  const sources = response?.sources || [];
  const tools = response?.tool_trace || [];

  return (
    <section className="pilotPage ticketsPage">
      <div className="ticketWorkspace">
        <section className="assistantPanel">
          <header className="assistantHeader">
            <div><Bot size={26} /><h1>Support Assistant Alpha</h1></div>
            <span>Session ID: #7892X</span>
            <button className="ghostButton" onClick={() => notify(`${messages.length} messages in this session.`)}><History size={16} />History</button>
            <button className="ghostButton" onClick={resetSession}><X size={16} />End Session</button>
          </header>

          <div className="assistantMessages">
            {messages.map((message, index) => (
              <article key={index} className={`pilotBubble ${message.role}`}>
                <p>{message.text}</p>
                <span>{message.role === "user" ? "Logistics Admin" : `Pilot AI${message.confidence ? ` / ${message.confidence}` : ""}`}</span>
              </article>
            ))}

            <div className="toolCard">
              <strong><Settings size={15} />Executing Tools</strong>
              {(tools.length ? tools : [{ name: "fetch_order_details", status: "ready", summary: "Waiting for a ticket or order request." }]).map((tool, index) => (
                <p key={index}>&gt; {String(tool.name || "tool")} <span>{String(tool.status || "ok")}</span></p>
              ))}
            </div>

            {pendingAction && (
              <div className="actionBanner">
                <div><strong>Escalation requires confirmation</strong><p>{pendingAction.summary}</p></div>
                <button onClick={() => confirmPending(pendingAction.id)}>Confirm</button>
              </div>
            )}
          </div>

          <div className="promptDock">
            {prompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}
          </div>

          <form className="assistantComposer" onSubmit={submit}>
            <button type="button" className="plusButton" onClick={() => notify("Attach document flow is ready for production object storage integration.")}>+</button>
            <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question or request an action..." disabled={busy} />
            <button disabled={busy} aria-label="Send"><Send size={18} /></button>
          </form>
        </section>

        <aside className="ticketSide">
          <section className="contextCard">
            <Truck size={30} />
            <h2>Order Context: ORD-1001</h2>
            <dl>
              <div><dt>Status</dt><dd><span className="statusPill">In Transit</span></dd></div>
              <div><dt>Client</dt><dd>Northstar Logistics Inc.</dd></div>
              <div><dt>Origin</dt><dd>Chicago, IL (ORD)</dd></div>
              <div><dt>Destination</dt><dd>Atlanta, GA (ATL)</dd></div>
              <div><dt>SLA Timer</dt><dd className="dangerText">6h 18m remaining</dd></div>
            </dl>
            <div className="slaBar"><span /></div>
          </section>

          <section className="contextCard documentCard">
            <div className="docTitle"><FileText size={28} /><h2>Document Discovery</h2><span>AI Extracted</span></div>
            {sources.slice(0, 3).map((source, index) => (
              <article key={index}>
                <strong>{String(source.name || "Document")}{source.page ? ` - p.${source.page}` : ""}</strong>
                <p>{String(source.excerpt || "").slice(0, 170)}...</p>
                <div><span>Confidence: {response?.confidence || "high"}</span><span>{String(source.authority || "source")}</span></div>
              </article>
            ))}
            {sources.length === 0 && (
              <article>
                <strong>Northstar MSA - Sec 4.2</strong>
                <p>Ask a question to extract matching policy and agreement passages.</p>
                <div><span>Confidence: ready</span><span>Source scan</span></div>
              </article>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

function AgreementsScreen({ shareAgreement, downloadAgreement, notify }: { shareAgreement: () => void; downloadAgreement: () => void; notify: (message: string) => void }) {
  return (
    <section className="pilotPage agreementsPage">
      <section className="agreementHero">
        <div>
          <p><FileText size={14} />Enterprise Agreement <span>Active</span></p>
          <h1>Northstar Logistics Master Service Agreement</h1>
          <p>Comprehensive framework agreement outlining service levels, pricing, liability, and operational procedures for regional distributions.</p>
          <dl>
            <div><dt>Signatory</dt><dd>Sarah Jenkins, VP Ops</dd></div>
            <div><dt>Effective Date</dt><dd>Oct 01, 2023</dd></div>
            <div><dt>Renewal</dt><dd>Sep 30, 2025</dd></div>
            <div><dt>Contract ID</dt><dd>NSL-MSA-2023-V2</dd></div>
          </dl>
        </div>
        <div className="heroButtons"><button className="lightButton" onClick={shareAgreement}><Share2 size={16} />Share</button><button onClick={downloadAgreement}><Download size={16} />Download PDF</button></div>
      </section>

      <div className="agreementLayout">
        <section className="clausesPanel">
          <h2>Key Clauses</h2>
          <Clause number="4.2" title="Service Level Commitments" tone="orange" text="Northstar receives account-specific response targets. Signed customer agreements override default global policies when sources conflict." notify={notify} />
          <Clause number="7.1" title="Liability Limits" tone="teal" text="Liability and special operational terms should be evaluated before issuing credits or policy exceptions." notify={notify} />
          <section className="hierarchyCard">
            <h2>Document Hierarchy</h2>
            <ul>
              <li><strong>Master Service Agreement (Current)</strong><span>Base contract signed Oct 01, 2023</span></li>
              <li><strong>Addendum A: European Operations</strong><span>Added Jan 15, 2024</span></li>
              <li><strong>Schedule 1: Pricing Matrix 2024</strong><span>Updated Jan 01, 2024</span></li>
            </ul>
          </section>
        </section>

        <aside className="conflictPanel">
          <div className="conflictHead"><Sparkles size={19} /><strong>AI Conflict Analysis</strong><span>2 overrides found</span></div>
          <p>Scanning agreement against standard global policies...</p>
          <ConflictCard title="Payment Terms Extension" agreement="Net 60 days" standard="Net 30 days" notify={notify} />
          <ConflictCard title="Custom Fuel Surcharge" agreement="Capped at 15% regional avg" standard="Floating based on national index" notify={notify} />
        </aside>
      </div>
    </section>
  );
}

function NotificationsPanel({ queue, refreshData }: { queue: EscalationQueue; refreshData: () => void }) {
  const openEscalations = queue.escalations.filter((item) => item.status !== "verified");
  return (
    <section className="topPopover notificationsPanel">
      <h3>Notifications</h3>
      <button onClick={refreshData}>Refresh Data Pack</button>
      {queue.pending_actions.length === 0 && openEscalations.length === 0 && <p>No pending admin actions.</p>}
      {queue.pending_actions.map((item) => <p key={item.id}><strong>Pending:</strong> {item.summary}</p>)}
      {openEscalations.map((item) => <p key={item.id}><strong>Escalation:</strong> {item.id} needs review.</p>)}
    </section>
  );
}

function SettingsPanel() {
  return (
    <section className="topPopover settingsPanel">
      <h3>Workspace Settings</h3>
      <label><input type="checkbox" defaultChecked /> Document-grounded answers</label>
      <label><input type="checkbox" defaultChecked /> Require confirmation for escalations</label>
      <label><input type="checkbox" defaultChecked /> Cost-aware model routing</label>
      <label><input type="checkbox" /> Dense data mode</label>
    </section>
  );
}

function TimeTabs() {
  const [range, setRange] = useState("1H");
  return (
    <div className="timeTabs">
      {["1H", "24H", "7D"].map((item) => <button key={item} className={range === item ? "active" : ""} onClick={() => setRange(item)}>{item}</button>)}
    </div>
  );
}

function MetricCard({ label, value, trend, icon, ring, onClick }: { label: string; value: string; trend: string; icon: ReactNode; ring?: boolean; onClick: () => void }) {
  return (
    <button className="pilotCard metricCard" onClick={onClick}>
      <div><span>{label}</span>{icon}</div>
      <strong>{value}</strong>
      <p>{trend}</p>
      {ring ? <i className="metricRing" /> : <i className="metricLine" />}
    </button>
  );
}

function ActivityRow({ icon, title, text, time, danger }: { icon: ReactNode; title: string; text: string; time: string; danger?: boolean }) {
  return (
    <article className="activityRow">
      <span className={danger ? "dangerIcon" : ""}>{icon}</span>
      <div><strong>{title}</strong><p>{text}</p></div>
      <time>{time}</time>
    </article>
  );
}

function FilterGroup({ title, values }: { title: string; values: string[] }) {
  return (
    <fieldset className="filterGroup">
      <legend>{title}</legend>
      {values.map((value, index) => (
        <label key={value}><input type="checkbox" defaultChecked={index < 2} />{value}</label>
      ))}
    </fieldset>
  );
}

function MetricMini({ title, value, tone }: { title: string; value: string; tone: string }) {
  return (
    <section className={`metricMini ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{tone === "danger" ? "+14%" : tone === "success" ? "Target: 98%" : "Regional"}</p>
    </section>
  );
}

function AnomalyCard({ item, onAction }: { item: { id: string; level: string; title: string; text: string; meta: string; action: string }; onAction: (item: { id: string; level: string; title: string; text: string; meta: string; action: string }) => void }) {
  return (
    <article className={`anomalyCard ${item.level}`}>
      <div>
        <span>{item.level}</span><small>{item.id} / 14 mins ago</small>
        <h3>{item.title}</h3>
        <p>{item.text}</p>
        <footer>{item.meta}</footer>
      </div>
      <button onClick={() => onAction(item)}>{item.action}</button>
    </article>
  );
}

function ReviewColumn({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : [];
  return (
    <section className="reviewColumn">
      <h3>{title}</h3>
      {items.length > 0 ? children : <p className="emptyText">{empty}</p>}
    </section>
  );
}

function Clause({ number, title, text, tone, notify }: { number: string; title: string; text: string; tone: string; notify: (message: string) => void }) {
  return (
    <article className={`clauseCard ${tone}`}>
      <strong>{number} {title}</strong>
      <p>{text}</p>
      <button onClick={() => notify(`Opened cross-reference for clause ${number}.`)}>Cross-reference: current support policy</button>
    </article>
  );
}

function ConflictCard({ title, agreement, standard, notify }: { title: string; agreement: string; standard: string; notify: (message: string) => void }) {
  return (
    <article className="conflictCard">
      <strong><AlertTriangle size={15} />{title}</strong>
      <p><b>Agreement:</b> {agreement}</p>
      <p><b>Standard Policy:</b> {standard}</p>
      <button onClick={() => notify(`AI suggestion prepared for ${title}.`)}><Sparkles size={13} />View AI suggestion for harmonization</button>
    </article>
  );
}
