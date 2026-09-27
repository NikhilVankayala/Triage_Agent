import { useState, useEffect } from "react";

const API = "http://localhost:8000";

type Request = {
  id: number;
  raw_text: string;
  status: string;
  created_at: string;
};

type Action = {
  id: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  result: Record<string, unknown> | null;
};

function App() {
  const [requests, setRequests] = useState<Request[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [newText, setNewText] = useState("");
  const [busy, setBusy] = useState(false);

  // Load the request list on mount.
  useEffect(() => {
    loadRequests();
  }, []);

  function loadRequests() {
    fetch(`${API}/requests`)
      .then((r) => r.json())
      .then((data) => setRequests(data.requests));
  }

  // Create a new request from the text box, then refresh the list.
  async function createRequest() {
    if (!newText.trim()) return;
    await fetch(`${API}/requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: newText }),
    });
    setNewText("");
    loadRequests();
  }

  // When a request is selected, load its proposed actions.
  function selectRequest(id: number) {
    setSelectedId(id);
    loadActions(id);
  }

  function loadActions(id: number) {
    fetch(`${API}/requests/${id}/actions`)
      .then((r) => r.json())
      .then((data) => setActions(data.actions));
  }

  // Run the agent on the selected request, then refresh its actions.
  async function triage(id: number) {
    setBusy(true);
    try {
      await fetch(`${API}/requests/${id}/triage`, { method: "POST" });
      loadActions(id);
    } finally {
      setBusy(false);
    }
  }

  // Approve or reject a proposed action, then refresh the list.
  async function resolve(actionId: number, decision: "approve" | "reject") {
    await fetch(`${API}/actions/${actionId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    if (selectedId !== null) loadActions(selectedId);
  }

  const selectedRequest = requests.find((r) => r.id === selectedId);

  return (
    <div style={{ display: "flex", gap: 24, padding: 24, fontFamily: "system-ui, sans-serif" }}>
      {/* Left column: create form + inbox */}
      <div style={{ flex: "0 0 340px" }}>
        <h1 style={{ fontSize: 22 }}>Triage Agent</h1>

        <div style={{ marginBottom: 16 }}>
          <textarea
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder="Paste a customer message…"
            rows={3}
            style={{ width: "100%", padding: 8, borderRadius: 8, boxSizing: "border-box" }}
          />
          <button
            onClick={createRequest}
            style={{ marginTop: 6, padding: "6px 14px", cursor: "pointer" }}
          >
            Create request
          </button>
        </div>

        {requests.map((request) => (
          <div
            key={request.id}
            onClick={() => selectRequest(request.id)}
            style={{
              padding: "10px 12px",
              marginBottom: 8,
              border: "1px solid #333",
              borderRadius: 8,
              cursor: "pointer",
              background: request.id === selectedId ? "#2a2a2a" : "transparent",
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.6 }}>
              #{request.id} · {request.status}
            </div>
            <div>{request.raw_text}</div>
          </div>
        ))}
      </div>

      {/* Right column: detail + proposed actions */}
      <div style={{ flex: 1 }}>
        {selectedRequest ? (
          <>
            <h2 style={{ fontSize: 18 }}>Request #{selectedRequest.id}</h2>
            <p style={{ opacity: 0.8 }}>{selectedRequest.raw_text}</p>

            <button
              onClick={() => triage(selectedRequest.id)}
              disabled={busy}
              style={{ padding: "8px 16px", marginBottom: 16, cursor: "pointer" }}
            >
              {busy ? "Running agent…" : "Run triage"}
            </button>

            <h3 style={{ fontSize: 15 }}>Proposed actions</h3>
            {actions.length === 0 && <p style={{ opacity: 0.6 }}>No actions yet.</p>}
            {actions.map((action) => (
              <div
                key={action.id}
                style={{
                  padding: 12,
                  marginBottom: 10,
                  border: "1px solid #333",
                  borderRadius: 8,
                }}
              >
                <div style={{ fontWeight: 600 }}>{action.tool_name}</div>
                <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", opacity: 0.8 }}>
                  {JSON.stringify(action.arguments, null, 2)}
                </pre>
                <div style={{ fontSize: 13, marginBottom: 8 }}>
                  Status: <strong>{action.status}</strong>
                </div>
                {action.status === "pending" && (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => resolve(action.id, "approve")} style={{ cursor: "pointer" }}>
                      Approve
                    </button>
                    <button onClick={() => resolve(action.id, "reject")} style={{ cursor: "pointer" }}>
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </>
        ) : (
          <p style={{ opacity: 0.6 }}>Select a request to see its proposed actions.</p>
        )}
      </div>
    </div>
  );
}

export default App;