import { useEffect, useMemo, useState } from "react";
import "./App.css";

// Default to API on 4177 unless overridden.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:4177";

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

function parseTrials(nctRaw) {
  if (!nctRaw) return [];
  const toList = Array.isArray(nctRaw)
    ? nctRaw
    : typeof nctRaw === "string"
      ? nctRaw.split(/[\n;,|]/)
      : [];
  return toList
    .map((v) => (typeof v === "string" ? v.trim() : String(v).trim()))
    .filter(Boolean)
    .map((line) => {
      const m = line.match(/(NCT\d{4,10})(.*)/i);
      const id = m ? m[1].toUpperCase() : line;
      const rest = m ? m[2].trim() : "";
      const desc = rest.replace(/^[\s:–-]+/, "").trim();
      return { id, desc };
    });
}

const Pill = ({ children, kind = "default" }) => (
  <span className={`pill ${kind}`}>{children}</span>
);

const SectionHeader = ({ title, right }) => (
  <div className="panel-header">
    <h3>{title}</h3>
    <div className="panel-actions">{right}</div>
  </div>
);

function EvidenceTable({ items }) {
  if (!items?.length) {
    return <div className="muted">No evidence items found.</div>;
  }

  const cols = [
    { key: "feature_names", label: "Feature" },
    { key: "variant_names", label: "Variant" },
    { key: "variant_origin", label: "Origin" },
    { key: "disease_name", label: "Disease" },
    { key: "therapy_names", label: "Therapy" },
    { key: "therapy_ncit_ids", label: "Therapy NCIt" },
    { key: "therapy_rxcui_ids", label: "RxCUI" },
    { key: "evidence_type", label: "Type" },
    { key: "evidence_level", label: "Level" },
    { key: "evidence_direction", label: "Direction" },
    { key: "evidence_significance", label: "Significance" },
    { key: "clinical_trial_nct_ids", label: "NCT IDs" },
    { key: "chromosome", label: "Chr" },
    { key: "reference_build", label: "Build" },
    { key: "start_position", label: "Start" },
    { key: "stop_position", label: "Stop" },
    { key: "variant_hgvs_descriptions", label: "HGVS" },
    { key: "cancer_cell_fraction", label: "CCF" },
    { key: "cohort_size", label: "Cohort" },
    { key: "source_title", label: "Source Title", tooltip: true },
    { key: "source_publication_year", label: "Year" },
    { key: "source_journal", label: "Journal", tooltip: true },
    { key: "source_page_numbers", label: "Pages" },
    { key: "verbatim_quote", label: "Quote", tooltip: true },
    { key: "extraction_confidence", label: "Confidence" },
    { key: "extraction_reasoning", label: "Reasoning", tooltip: true },
  ];

  const normalizeRow = (item) => {
    const ncitList = Array.isArray(item.therapies)
      ? item.therapies.map((t) => t.ncit_id).filter(Boolean)
      : [];
    const rxcuiList = Array.isArray(item.therapies)
      ? item.therapies.map((t) => t.rxcui).filter(Boolean)
      : [];
    const safetyList = Array.isArray(item.therapies)
      ? item.therapies
          .map((t) => {
            if (t?.safety_profile?.top_adverse_events?.length) {
              const top = t.safety_profile.top_adverse_events
                .slice(0, 3)
                .map((ae) => `${ae.term} (${ae.count})`)
                .join(", ");
              return `${t.name}: ${top}`;
            }
            return null;
          })
          .filter(Boolean)
      : [];
    const clinicalTrials =
      item.clinical_trial_nct_ids ||
      (Array.isArray(item.therapies)
        ? item.therapies.flatMap((t) => t.clinical_trial_ids || [])
        : []);
    return {
      ...item,
      therapy_ncit_ids: ncitList.length ? ncitList.join(", ") : "—",
      therapy_rxcui_ids: rxcuiList.length ? rxcuiList.join(", ") : "—",
      extraction_confidence:
        typeof item.extraction_confidence === "number"
          ? `${Math.round(item.extraction_confidence * 100)}%`
          : item.extraction_confidence || "—",
      extraction_reasoning: item.extraction_reasoning || "—",
      safety_profiles: safetyList.length ? safetyList.join(" | ") : "—",
      clinical_trial_nct_ids: clinicalTrials && clinicalTrials.length ? clinicalTrials.join(", ") : "—",
      start_position: item.start_position ?? "—",
      stop_position: item.stop_position ?? "—",
      reference_build: item.reference_build || "—",
      variant_origin: item.variant_origin || "—",
      cancer_cell_fraction:
        typeof item.cancer_cell_fraction === "number"
          ? item.cancer_cell_fraction
          : item.cancer_cell_fraction || "—",
      source_publication_year: item.source_publication_year || "—",
      source_journal: item.source_journal || "—",
      source_page_numbers: item.source_page_numbers || "—",
      variant_hgvs_descriptions: item.variant_hgvs_descriptions || item.variant_hgvs || [],
    };
  };

  return (
    <div className="table-wrapper">
      <table className="table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((raw, idx) => {
            const item = normalizeRow(raw);
            return (
              <tr key={idx}>
                {cols.map((c) => (
                  <td
                    key={c.key}
                    className={c.tooltip ? "ellipsis" : ""}
                    title={c.tooltip ? (Array.isArray(item[c.key]) ? item[c.key].join(", ") : item[c.key] || "") : undefined}
                  >
                    {Array.isArray(item[c.key])
                      ? item[c.key].length
                        ? item[c.key].join(", ")
                        : "—"
                      : item[c.key] || "—"}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
function Collapse({ title, summary, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card">
      <div className="collapse-header" onClick={() => setOpen((o) => !o)}>
        <div>
          <div className="card-title">{title}</div>
          {summary && <div className="muted small">{summary}</div>}
        </div>
        <div className="muted">{open ? "▲" : "▼"}</div>
      </div>
      {open && <div className="collapse-body">{children}</div>}
    </div>
  );
}

function PhaseSummaries({ phases }) {
  const entries = [
    { key: "reader", label: "Reader (01)", data: phases.reader, desc: "PDF → structured text" },
    { key: "planner", label: "Planner (02)", data: phases.planner, desc: "Strategy & expected items" },
    { key: "extractor", label: "Extractor (03)", data: phases.extractor, desc: "Draft evidence items" },
    { key: "critic", label: "Critic (03b)", data: phases.critic, desc: "Validation & feedback" },
    { key: "normalizer", label: "Normalizer (04)", data: phases.normalizer, desc: "IDs & final items" },
  ];

  return (
    <div className="phase-grid">
      {entries.map(({ key, label, data, desc }) => (
        <div className="card" key={key}>
          <div className="card-title">{label}</div>
          {data ? (
            <>
              {data.summary && <div className="muted small">{data.summary}</div>}
              {data.items && (
                <div className="muted small">
                  Items: <strong>{data.items.length}</strong>
                </div>
              )}
              {desc && <div className="muted small">{desc}</div>}
            </>
          ) : (
            <div className="muted small">No data</div>
          )}
        </div>
      ))}
    </div>
  );
}

function PhaseDetails({ phases }) {
  const renderList = (items) =>
    !items || !items.length ? (
      <div className="muted small">No items</div>
    ) : (
      <ul className="plain-list">
        {items.map((it, idx) => (
          <li key={idx}>
            <strong>{it.variant_names || it.feature_names}</strong> — {it.therapy_names || "—"} —{" "}
            {it.disease_name || "—"} ({it.evidence_type || "type"})
          </li>
        ))}
      </ul>
    );

  return (
    <div className="checkpoint-grid">
      <Collapse title="Reader (01) – paper content" summary={phases.reader?.summary}>
        <pre className="pre small">
          {phases.reader?.content ? JSON.stringify(phases.reader.content, null, 2) : "No content"}
        </pre>
      </Collapse>

      <Collapse title="Planner (02) – plan" summary={phases.planner?.summary}>
        <pre className="pre small">
          {phases.planner?.plan ? JSON.stringify(phases.planner.plan, null, 2) : "No plan"}
        </pre>
      </Collapse>

      <Collapse
        title="Extractor (03) – draft extractions"
        summary={phases.extractor?.items ? `${phases.extractor.items.length} items` : ""}
      >
        {renderList(phases.extractor?.items)}
        <pre className="pre small">
          {phases.extractor?.raw ? JSON.stringify(phases.extractor.raw, null, 2) : "No data"}
        </pre>
      </Collapse>

      <Collapse
        title="Critic (03b) – feedback"
        summary={
          phases.critic?.critique
            ? `${phases.critic?.critique.overall_assessment || ""}`
            : ""
        }
      >
        {phases.critic?.critique ? (
          <>
            <div className="muted small">
              Assessment: <strong>{phases.critic.critique.overall_assessment}</strong>
            </div>
            <div className="muted small">
              Missing items: {phases.critic.critique.missing_items?.length || 0} · Extra items:{" "}
              {phases.critic.critique.extra_items?.length || 0}
            </div>
            <pre className="pre small">{JSON.stringify(phases.critic.critique, null, 2)}</pre>
          </>
        ) : (
          <div className="muted small">No data</div>
        )}
      </Collapse>

      <Collapse
        title="Normalizer (04) – final extractions"
        summary={phases.normalizer?.items ? `${phases.normalizer.items.length} items` : ""}
      >
        {renderList(phases.normalizer?.items)}
        <pre className="pre small">
          {phases.normalizer?.raw ? JSON.stringify(phases.normalizer.raw, null, 2) : "No data"}
        </pre>
      </Collapse>
    </div>
  );
}

function Timeline({ events }) {
  if (!events?.length) return <div className="muted">No timeline events.</div>;
  return (
    <div className="timeline">
      {events.slice(-200).map((ev, idx) => (
        <div className="timeline-item" key={idx}>
          <div className="timeline-meta">
            <span className="pill">{ev.hook || ev.event}</span>
            <span className="muted small">{ev.ts}</span>
          </div>
          <div className="timeline-body">
            <div className="muted small">
              tool: {ev.tool || "—"} · input: {ev.input_keys?.join(", ") || "—"}
            </div>
            {ev.output_summary && <div className="muted small">result: {ev.output_summary}</div>}
            {ev.text && <div className="muted small">msg: {ev.text}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

function TagList({ items, hrefBuilder, title }) {
  if (!items?.length) return <span className="muted">—</span>;
  return (
    <div className="tag-row" title={title}>
      {items.map((it) => (
        <a
          key={it}
          className="pill link-pill"
          href={hrefBuilder ? hrefBuilder(it) : undefined}
          target={hrefBuilder ? "_blank" : undefined}
          rel="noreferrer"
        >
          {it}
        </a>
      ))}
    </div>
  );
}

function PlanPanel({ plan }) {
  if (!plan) return null;
  return (
    <div className="panel">
      <SectionHeader title="Extraction Plan" />
      <div className="plan-grid">
        <div className="card">
          <div className="muted small">Expected items</div>
          <div className="big">{plan.expected_items ?? "—"}</div>
          <div className="muted small">{plan.paper_type || "Paper type unknown"}</div>
        </div>
        <div className="card">
          <div className="card-title">Key variants</div>
          <pre className="pre small">{plan.key_variants || "—"}</pre>
        </div>
        <div className="card">
          <div className="card-title">Key therapies</div>
          <pre className="pre small">{plan.key_therapies || "—"}</pre>
        </div>
        <div className="card">
          <div className="card-title">Key diseases</div>
          <pre className="pre small">{plan.key_diseases || "—"}</pre>
        </div>
      </div>
      <div className="card">
        <div className="card-title">Focus sections</div>
        <pre className="pre small">{plan.focus_sections || "—"}</pre>
      </div>
      <div className="card">
        <div className="card-title">Extraction notes</div>
        <pre className="pre small">{plan.extraction_notes || "—"}</pre>
      </div>
    </div>
  );
}

function CritiquePanel({ critique }) {
  if (!critique) return null;
  return (
    <div className="panel">
      <SectionHeader
        title="Final Critique"
        right={<Pill kind={critique.overall_assessment === "APPROVE" ? "success" : "warning"}>{critique.overall_assessment}</Pill>}
      />
      <div className="critique-grid">
        <Collapse title="Summary" defaultOpen>
          <pre className="pre small">{critique.summary || "No summary"}</pre>
        </Collapse>
        <Collapse title="Item feedback">
          <pre className="pre small">{critique.item_feedback || "No item feedback"}</pre>
        </Collapse>
        <Collapse title="Missing items">
          <pre className="pre small">{critique.missing_items || "No missing items"}</pre>
        </Collapse>
        <Collapse title="Extra items">
          <pre className="pre small">{critique.extra_items || "No extra items"}</pre>
        </Collapse>
      </div>
    </div>
  );
}

function StatsGrid({ evidence }) {
  if (!evidence?.length) return null;

  const geneCounts = {};
  const therapyCounts = {};
  const typeCounts = {};
  const directionCounts = {};
  evidence.forEach((item) => {
    (item.feature_names || []).forEach((g) => {
      geneCounts[g] = (geneCounts[g] || 0) + 1;
    });
    (item.therapy_names || []).forEach((t) => {
      therapyCounts[t] = (therapyCounts[t] || 0) + 1;
    });
    if (item.evidence_type) typeCounts[item.evidence_type] = (typeCounts[item.evidence_type] || 0) + 1;
    if (item.evidence_direction) directionCounts[item.evidence_direction] = (directionCounts[item.evidence_direction] || 0) + 1;
  });

  const top = (obj, n = 3) =>
    Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .slice(0, n);

  return (
    <div className="stats-grid">
      <div className="card">
        <div className="card-title">Top genes</div>
        <div className="tag-row">
          {top(geneCounts).map(([g, c]) => (
            <span key={g} className="pill">
              {g} · {c}
            </span>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="card-title">Top therapies</div>
        <div className="tag-row">
          {top(therapyCounts).map(([t, c]) => (
            <span key={t} className="pill">
              {t} · {c}
            </span>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="card-title">Types</div>
        <div className="tag-row">
          {Object.entries(typeCounts).map(([k, v]) => (
            <span key={k} className="pill">
              {k} · {v}
            </span>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="card-title">Directions</div>
        <div className="tag-row">
          {Object.entries(directionCounts).map(([k, v]) => (
            <span key={k} className="pill">
              {k} · {v}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function JsonModal({ open, title, data, onClose }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="card-title">{title}</div>
          <button className="pill" onClick={onClose}>
            Close
          </button>
        </div>
        <pre className="pre small modal-pre">{JSON.stringify(data, null, 2)}</pre>
      </div>
    </div>
  );
}

function App() {
  const [papers, setPapers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [output, setOutput] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [phases, setPhases] = useState({});
  const [sessionEvents, setSessionEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [runMessage, setRunMessage] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [pdfPathInput, setPdfPathInput] = useState("");
  const [jsonModal, setJsonModal] = useState({ open: false, title: "", data: null });
  const [activeTab, setActiveTab] = useState("output");
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState("ALL");
  const [directionFilter, setDirectionFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  function parseCheckpoints(raw) {
    const phases = { reader: null, planner: null, extractor: null, critic: null, normalizer: null };
    for (const cp of raw || []) {
      if (!cp?.name) continue;
      const name = cp.name.toLowerCase();
      const data = cp.data || {};
      if (name.startsWith("01")) {
        const nct =
          data.paper_content?.clinical_trial_nct_ids ||
          data.paper_content?.clinical_trial_nct ||
          data.paper_content?.clinical_trials;
        phases.reader = {
          summary: data.paper_content?.title || "Reader output",
          content: {
            title: data.paper_content?.title,
            authors: data.paper_content?.authors,
            journal: data.paper_content?.journal,
            year: data.paper_content?.year,
            paper_type: data.paper_content?.paper_type,
            num_pages: data.paper_content?.num_pages,
            abstract: data.paper_content?.abstract,
            sections: data.paper_content?.sections?.slice?.(0, 2),
            nct_ids: nct,
          },
        };
      } else if (name.startsWith("02")) {
        phases.planner = {
          summary: data.plan ? `Planned: ${data.plan.expected_items || "?"}` : "Planner plan",
          plan: data.plan,
        };
      } else if (name.startsWith("03_critic") || name.startsWith("03-critic") || (name.includes("critic") && name.includes("03"))) {
        phases.critic = {
          summary: (data.critique && data.critique.overall_assessment) || "Critic feedback",
          critique: data.critique,
        };
      } else if (name.startsWith("03")) {
        const items = data.extraction?.draft_extractions || [];
        phases.extractor = {
          summary: `Draft items: ${items.length}`,
          items,
          raw: items,
        };
      } else if (name.startsWith("04")) {
        const items = data.final_extractions || data.extraction?.final_extractions || [];
        phases.normalizer = {
          summary: `Final: ${items.length}`,
          items,
          raw: items,
        };
      }
    }
    return phases;
  }

  useEffect(() => {
    fetchJson(`${API_BASE}/api/papers`)
      .then((data) => setPapers(data.papers || []))
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setError("");
    Promise.all([
      fetchJson(`${API_BASE}/api/papers/${selected}/output`).catch(() => null),
      fetchJson(`${API_BASE}/api/papers/${selected}/checkpoints`).catch(() => ({ checkpoints: [] })),
      fetchJson(`${API_BASE}/api/papers/${selected}/session`).catch(() => ({ events: [] })),
    ])
      .then(([out, cps, ses]) => {
        setOutput(out?.output || null);
        setCheckpoints(cps?.checkpoints || []);
        setPhases(parseCheckpoints(cps?.checkpoints || []));
        setSessionEvents(ses?.events || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selected]);

  const pdfUrl = useMemo(() => {
    if (!selected) return null;
    return `${API_BASE}/api/papers/${selected}/pdf`;
  }, [selected]);

  const trials = useMemo(() => parseTrials(phases.reader?.content?.nct_ids), [phases]);
  const clean = (v) => (v && v !== "Unknown" ? v : "—");
  const formatSeconds = (timing) => {
    if (!timing?.seconds) return "—";
    const secs = Number(timing.seconds);
    if (Number.isNaN(secs)) return "—";
    const minutes = Math.floor(secs / 60);
    const remain = Math.round(secs % 60);
    return minutes ? `${minutes}m ${remain}s` : `${remain}s`;
  };
  const evidenceMeta = useMemo(() => {
    const items = output?.extraction?.evidence_items || [];
    const firstPmid = items.find((it) => it.pmid)?.pmid || output?.paper_info?.pmid;
    const firstPmcid = items.find((it) => it.pmcid)?.pmcid || output?.paper_info?.pmcid;
    return { pmid: firstPmid, pmcid: firstPmcid };
  }, [output]);

  const handleRun = async () => {
    try {
      setUploading(true);
      setRunMessage("");
      const form = new FormData();
      if (uploadFile) {
        form.append("file", uploadFile);
      } else if (pdfPathInput.trim()) {
        form.append("pdfPath", pdfPathInput.trim());
      } else {
        setRunMessage("Provide a PDF file or a PDF path.");
        setUploading(false);
        return;
      }
      const res = await fetch(`${API_BASE}/api/extract`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok || data.status === "error") {
        setRunMessage(data.error || data.stderr || "Run failed");
      } else {
        setRunMessage("Run started/finished. Refreshing paper list...");
        const refreshed = await fetchJson(`${API_BASE}/api/papers`);
        setPapers(refreshed.papers || []);
      }
    } catch (err) {
      setRunMessage(err.message);
    } finally {
      setUploading(false);
    }
  };

  const openJson = (title, data) => setJsonModal({ open: true, title, data });
  const closeJson = () => setJsonModal({ open: false, title: "", data: null });

  const paperTitle = phases.reader?.content?.title || output?.paper_info?.title || selected;
  const paperAuthors = phases.reader?.content?.authors || output?.paper_info?.author || "—";
  const paperJournal = phases.reader?.content?.journal || output?.paper_info?.journal || "—";
  const paperYear = phases.reader?.content?.year || output?.paper_info?.year || "—";
  const paperPages = phases.reader?.content?.num_pages || output?.paper_info?.num_pages || "—";
  const paperType = phases.reader?.content?.paper_type || output?.paper_info?.paper_type || "—";
  const evidenceItems = output?.extraction?.evidence_items || [];
  const filteredEvidence = useMemo(() => {
    return evidenceItems.filter((item) => {
      const matchesType = evidenceTypeFilter === "ALL" || item.evidence_type === evidenceTypeFilter;
      const matchesDir = directionFilter === "ALL" || item.evidence_direction === directionFilter;
      const haystack = JSON.stringify(item).toLowerCase();
      const matchesSearch = !searchTerm.trim() || haystack.includes(searchTerm.toLowerCase());
      return matchesType && matchesDir && matchesSearch;
    });
  }, [evidenceItems, evidenceTypeFilter, directionFilter, searchTerm]);
  const evidenceTypes = Array.from(new Set(evidenceItems.map((i) => i.evidence_type).filter(Boolean)));
  const directions = Array.from(new Set(evidenceItems.map((i) => i.evidence_direction).filter(Boolean)));

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Papers</h2>
        <div className="paper-list">
          {papers.map((p) => (
            <button
              key={p.id}
              className={`paper-btn ${selected === p.id ? "active" : ""}`}
              onClick={() => setSelected(p.id)}
            >
              <div className="paper-title">{p.id}</div>
              <div className="paper-meta">
                {p.hasOutput ? "✅ Output" : "…"} · {p.hasCheckpoints ? "💾 Checkpoints" : "…"}
              </div>
            </button>
          ))}
          {!papers.length && <div className="muted">No papers found.</div>}
        </div>
      </aside>

      <main className="main">
        <header className="header">
          <div>
            <h1>Evidence Extraction Viewer</h1>
            <p className="muted">Reader → Planner → Extractor → Normalizer</p>
          </div>
          <div className="header-pills">
            {loading && <Pill>Loading…</Pill>}
            {error && <Pill kind="error">{error}</Pill>}
          </div>
        </header>

        <div className="panel">
          <SectionHeader
            title="Upload or run a PDF"
            right={uploading && <Pill>Running…</Pill>}
          />
          <div className="run-form">
            <div className="field">
              <label>Upload PDF</label>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              />
            </div>
            <div className="field">
              <label>Or existing PDF path</label>
              <input
                type="text"
                value={pdfPathInput}
                onChange={(e) => setPdfPathInput(e.target.value)}
                placeholder="/absolute/path/to/paper.pdf"
              />
            </div>
            <button className="run-btn" onClick={handleRun} disabled={uploading}>
              Trigger Extraction
            </button>
            {runMessage && <div className="muted">{runMessage}</div>}
          </div>
        </div>

        {!selected && <div className="muted">Select a paper to view artifacts.</div>}

        {selected && (
          <div className="content">
            <div className="tab-bar">
              <button className={`tab-btn ${activeTab === "pdf" ? "active" : ""}`} onClick={() => setActiveTab("pdf")}>
                Original PDF
              </button>
              <button className={`tab-btn ${activeTab === "output" ? "active" : ""}`} onClick={() => setActiveTab("output")}>
                Final Output
              </button>
              <button className={`tab-btn ${activeTab === "plan" ? "active" : ""}`} onClick={() => setActiveTab("plan")}>
                Plan & Critique
              </button>
              <button className={`tab-btn ${activeTab === "checkpoints" ? "active" : ""}`} onClick={() => setActiveTab("checkpoints")}>
                Checkpoints
              </button>
              <button className={`tab-btn ${activeTab === "timeline" ? "active" : ""}`} onClick={() => setActiveTab("timeline")}>
                Timeline
              </button>
            </div>

            {activeTab === "pdf" && (
              <div className="pane">
                <SectionHeader
                  title="Original PDF"
                  right={
                    pdfUrl ? (
                      <a className="pill link-pill" href={pdfUrl} target="_blank" rel="noreferrer">
                        Open in new tab
                      </a>
                    ) : null
                  }
                />
                {pdfUrl ? (
                  <iframe className="pdf-frame" src={pdfUrl} title={selected} />
                ) : (
                  <div className="muted">PDF not available.</div>
                )}
              </div>
            )}

            {activeTab === "output" && (
              <div className="pane">
                <SectionHeader
                  title="Final Output"
                  right={
                    output ? (
                      <button className="pill" onClick={() => openJson("Final output JSON", output)}>
                        View JSON
                      </button>
                    ) : null
                  }
                />
                {output ? (
                  <>
                    <div className="card paper-meta">
                      <div className="card-title">{paperTitle}</div>
                      <div className="muted small">Authors: {paperAuthors}</div>
                      <div className="muted small">Journal: {paperJournal}</div>
                      <div className="muted small">Year: {paperYear} · Pages: {paperPages}</div>
                      <div className="muted small">Type: {paperType}</div>
                      <div className="pill-row">
                        <Pill>Items: {output.extraction?.items ?? "—"}</Pill>
                        <Pill>Iterations: {output.extraction?.iterations ?? "—"}</Pill>
                        <Pill>Duration: {formatSeconds(output.timing)}</Pill>
                      </div>
                      <div className="muted small">PMID: {clean(evidenceMeta.pmid)} · PMCID: {clean(evidenceMeta.pmcid)}</div>
                      <div className="muted small">
                        NCT IDs:
                        <TagList
                          items={trials.map((t) => t.id)}
                          hrefBuilder={(id) => `https://clinicaltrials.gov/study/${id}`}
                          title="Reader NCT IDs"
                        />
                      </div>
                      {output.log_file && <div className="muted small">Log file: {output.log_file}</div>}
                    </div>

                    <StatsGrid evidence={filteredEvidence} />

                    <div className="filters">
                      <div className="filter-group">
                        <label>Evidence type</label>
                        <select value={evidenceTypeFilter} onChange={(e) => setEvidenceTypeFilter(e.target.value)}>
                          <option value="ALL">All</option>
                          {evidenceTypes.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="filter-group">
                        <label>Direction</label>
                        <select value={directionFilter} onChange={(e) => setDirectionFilter(e.target.value)}>
                          <option value="ALL">All</option>
                          {directions.map((d) => (
                            <option key={d} value={d}>
                              {d}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="filter-group">
                        <label>Search</label>
                        <input
                          type="text"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder="Filter text"
                        />
                      </div>
                      <div className="pill muted small">{filteredEvidence.length} / {evidenceItems.length} items</div>
                    </div>

                    <EvidenceTable items={filteredEvidence} />
                  </>
                ) : (
                  <div className="muted">No final output yet.</div>
                )}
              </div>
            )}

            {activeTab === "plan" && (
              <div className="pane">
                {output?.plan ? <PlanPanel plan={output.plan} /> : <div className="muted">No plan available.</div>}
                {output?.final_critique ? <CritiquePanel critique={output.final_critique} /> : <div className="muted">No critique available.</div>}
              </div>
            )}

            {activeTab === "checkpoints" && (
              <div className="panel">
                <SectionHeader
                  title="Agent Checkpoints (01–04)"
                  right={
                    checkpoints.length ? (
                      <div className="tag-row">
                        {checkpoints.map((cp, idx) => (
                          <button
                            key={idx}
                            className="pill"
                            onClick={() => openJson(cp.name || `Checkpoint ${idx + 1}`, cp.data)}
                          >
                            View {cp.name || `Checkpoint ${idx + 1}`}
                          </button>
                        ))}
                      </div>
                    ) : null
                  }
                />
                <PhaseSummaries phases={phases} />
                <PhaseDetails phases={phases} />
              </div>
            )}

            {activeTab === "timeline" && (
              <div className="panel">
                <SectionHeader title="Timeline (tool calls & hooks)" />
                <Timeline events={sessionEvents} />
              </div>
            )}
          </div>
        )}
      </main>

      <JsonModal open={jsonModal.open} title={jsonModal.title} data={jsonModal.data} onClose={closeJson} />
    </div>
  );
}

export default App;
