"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Bell, Bot, CheckCircle2, FileText, Paperclip, Send, ShieldAlert, Truck, UserRound } from "lucide-react";
import { apiGet, apiPost, ChatResponse, EscalationQueue, User, WS_BASE } from "@/lib/api";

type Message = {
  role: "user" | "agent";
  text: string;
  confidence?: string;
  sources?: Array<Record<string, unknown>>;
};

const quickPrompts = [
  "Where is ORD-1001 and is there any SLA risk?",
  "Can Northstar cancel ORD-1001 without a cancellation fee?",
  "What support SLA applies to Northstar for a P1 incident?",
  "Escalate this to a human agent for billing review."
];

export default function CustomerSupportPortal() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState("northstar_user");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState<"shipments" | "support">("support");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      text: "Hello. I can help with shipment tracking, contract inquiries, SLA monitoring, credits, cancellations, and escalations.",
      confidence: "high"
    }
  ]);
  const [pendingAction, setPendingAction] = useState<Record<string, unknown> | null>(null);
  const [queue, setQueue] = useState<EscalationQueue>({ escalations: [], pending_actions: [] });
  const [toast, setToast] = useState("");
  const [connection, setConnection] = useState<"connecting" | "live" | "offline">("connecting");
  const socketRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const activeUser = useMemo(() => users.find((user) => user.user_id === userId), [users, userId]);
  const latestResponse = queue.escalations.find((item) => item.response);

  useEffect(() => {
    apiGet<{ users: User[] }>("/api/users").then((data) => setUsers(data.users.filter((user) => user.role === "customer")));
  }, []);

  useEffect(() => {
    const socket = new WebSocket(`${WS_BASE}/ws/chat`);
    socketRef.current = socket;
    setConnection("connecting");

    socket.onopen = () => setConnection("live");
    socket.onclose = () => setConnection("offline");
    socket.onerror = () => setConnection("offline");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "status") {
        setMessages((current) => [...current.slice(0, -1), { role: "agent", text: payload.message, confidence: "high" }]);
      }
      if (payload.type === "answer") {
        const response = payload.response as ChatResponse;
        setMessages((current) => [
          ...current.slice(0, -1),
          {
            role: "agent",
            text: response.answer || response.error || "No response.",
            confidence: response.confidence,
            sources: response.sources
          }
        ]);
        setPendingAction((response.pending_action as Record<string, unknown>) || null);
        setBusy(false);
        void loadEscalations();
      }
      if (payload.type === "error") {
        setMessages((current) => [...current.slice(0, -1), { role: "agent", text: payload.error || "WebSocket chat failed.", confidence: "low" }]);
        setBusy(false);
      }
    };

    return () => socket.close();
  }, []);

  useEffect(() => {
    void loadEscalations();
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pendingAction, latestResponse]);

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  }

  async function loadEscalations() {
    const data = await apiGet<EscalationQueue>("/api/escalations", userId);
    setQueue(data);
  }

  async function send(message: string) {
    const clean = message.trim();
    if (!clean) return;
    setActiveTab("support");
    setBusy(true);
    setMessages((current) => [
      ...current,
      { role: "user", text: clean },
      { role: "agent", text: connection === "live" ? "Sending over secure live chat..." : "Live chat is reconnecting..." }
    ]);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ user_id: userId, message: clean }));
      return;
    }
    setMessages((current) => [...current.slice(0, -1), { role: "agent", text: "Live chat connection is offline. Please refresh or restart the backend WebSocket server.", confidence: "low" }]);
    setBusy(false);
  }

  async function confirmPendingAction() {
    if (!pendingAction?.id) return;
    const result = await apiPost<{ executed?: Record<string, unknown>; detail?: string }>("/api/actions/confirm", { user_id: userId, action_id: pendingAction.id }, userId);
    setMessages((current) => [
      ...current,
      {
        role: "agent",
        text: result.executed ? `Confirmed. Human support ticket ${result.executed.id} has been created for your account.` : result.detail || "Action failed.",
        confidence: result.executed ? "high" : "low"
      }
    ]);
    setPendingAction(null);
    await loadEscalations();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = input;
    setInput("");
    void send(value);
  }

  return (
    <main className="customerAssistantShell">
      <header className="customerAssistantTop">
        <div className="customerLogo"><span>PP</span><strong>ParcelPilot</strong></div>
        <nav>
          <button className={activeTab === "shipments" ? "active" : ""} onClick={() => setActiveTab("shipments")}>My Shipments</button>
          <button className={activeTab === "support" ? "active" : ""} onClick={() => setActiveTab("support")}>Support</button>
        </nav>
        <div className="customerAccount">
          <select value={userId} onChange={(event) => setUserId(event.target.value)}>
            {users.length === 0 && <option value={userId}>Loading account...</option>}
            {users.map((user) => <option key={user.user_id} value={user.user_id}>{user.display_name}</option>)}
          </select>
          <Bell size={18} />
          <div className="customerAvatar"><UserRound size={16} /></div>
        </div>
      </header>

      {activeTab === "shipments" && (
        <section className="customerShipments">
          <h1>My Shipments</h1>
          <div className="shipmentGrid">
            <ShipmentCard id="ORD-1001" account="Northstar Logistics" status="Pickup delayed" risk="SLA watch" onAsk={() => send("Where is ORD-1001 and is there any SLA risk?")} />
            <ShipmentCard id="ORD-2002" account="LumenWorks" status="In transit" risk="No active breach" onAsk={() => send("Can I see LumenWorks order ORD-2002?")} />
          </div>
        </section>
      )}

      {activeTab === "support" && (
        <section className="customerAssistantStage">
          <div className="assistantIntro">
            <div className="assistantBotMark"><Bot size={28} /><i /></div>
            <h1>ParcelPilot Assistant</h1>
            <p>Hello! I am your AI logistics partner. I can help with shipment tracking, contract inquiries, SLA monitoring, and escalations.</p>
            <span>{activeUser?.display_name || "Customer"} / {activeUser?.account_id || "Account scoped"} / {connection}</span>
          </div>

          <div className="policyChip"><AlertTriangle size={14} />Policy check: billing adjustments</div>

          <section className="customerConversation">
            {messages.map((message, index) => (
              <article key={index} className={`customerMessage ${message.role}`}>
                <div className="messageIcon">{message.role === "agent" ? <Bot size={15} /> : <UserRound size={15} />}</div>
                <div className="messageCard">
                  <p>{message.text}</p>
                  {message.sources && message.sources.length > 0 && (
                    <div className="sourceStrip">
                      {message.sources.slice(0, 3).map((source, sourceIndex) => (
                        <span key={sourceIndex}><FileText size={12} />{String(source.name || "Source")}{source.page ? ` p.${source.page}` : ""}</span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}

            {pendingAction && (
              <article className="customerMessage agent">
                <div className="messageIcon"><ShieldAlert size={15} /></div>
                <div className="messageCard escalationCard">
                  <h2>Escalate to Human Agent</h2>
                  <p>{String(pendingAction.summary || "A specialist can review this request.")}</p>
                  <div>
                    <button onClick={confirmPendingAction}>Confirm Escalation</button>
                    <button onClick={() => setPendingAction(null)}>Cancel</button>
                  </div>
                </div>
              </article>
            )}

            {latestResponse && (
              <article className="customerMessage agent">
                <div className="messageIcon success"><CheckCircle2 size={15} /></div>
                <div className="messageCard responseCard">
                  <h2>Human Support Response</h2>
                  <p>{latestResponse.response}</p>
                  <span>{latestResponse.id} / {latestResponse.status}</span>
                </div>
              </article>
            )}
            <div ref={bottomRef} />
          </section>

          <div className="customerQuickPrompts">
            {quickPrompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}
          </div>

          <form className="customerComposer" onSubmit={submit}>
            <button type="button" onClick={() => notify("Upload support documents requires production object storage.")}><Paperclip size={18} /></button>
            <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask about shipments, contracts, or account status..." disabled={busy} />
            <button disabled={busy} aria-label="Send"><Send size={20} /></button>
          </form>

          <p className="assistantFootnote">ParcelPilot AI operates within established SLA constraints.</p>
        </section>
      )}

      <footer className="customerFooter">
        <span>ParcelPilot Customer Portal</span>
        <a>Privacy Policy</a>
        <a>Terms of Service</a>
        <span>(c) 2024 ParcelPilot AI. All rights reserved.</span>
      </footer>

      {toast && <div className="nextToast">{toast}</div>}
    </main>
  );
}

function ShipmentCard({ id, account, status, risk, onAsk }: { id: string; account: string; status: string; risk: string; onAsk: () => void }) {
  return (
    <article className="customerShipmentCard">
      <Truck size={24} />
      <div><strong>{id}</strong><span>{account}</span></div>
      <p>{status}</p>
      <small>{risk}</small>
      <button onClick={onAsk}>Ask Assistant</button>
    </article>
  );
}
