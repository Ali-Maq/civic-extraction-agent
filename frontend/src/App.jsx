import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
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

function PdfViewer({ url, onError }) {
  const [numPages, setNumPages] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  if (!url) return <div className="muted">PDF not available.</div>;
  if (error) {
    if (onError) onError(error);
    return <div className="muted">PDF error: {error}</div>;
  }

  const next = () => setPage((p) => Math.min((numPages || p), p + 1));
  const prev = () => setPage((p) => Math.max(1, p - 1));

  return (
    <div className="pdf-viewer">
      <div className="pdf-controls">
        <button className="pill" onClick={prev} disabled={page <= 1}>
          ◀ Prev
        </button>
        <span className="muted small">
          Page {page} {numPages ? `of ${numPages}` : ""}
        </span>
        <button className="pill" onClick={next} disabled={numPages ? page >= numPages : false}>
          Next ▶
        </button>
        <a className="pill link-pill" href={url} target="_blank" rel="noreferrer">
          Download
        </a>
      </div>
      <div className="pdf-canvas">
        <Document
          file={{ url, httpHeaders: { Accept: "application/pdf" }, withCredentials: false }}
          onLoadSuccess={({ numPages: n }) => {
            setNumPages(n);
            setError("");
          }}
          onLoadError={(err) => setError(err?.message || "Failed to load PDF")}
        >
          <Page pageNumber={page} width={800} renderAnnotationLayer={false} renderTextLayer={false} />
        </Document>
      </div>
    </div>
  );
}

// Removed PdfViewer (react-pdf). Using iframe/embed fallback only.

function EvidenceCards({ items }) {
  if (!items?.length) return <div className="muted">No evidence items found.</div>;
  const normalize = (item) => ({
    ...item,
    therapies: item.therapies || [],
    therapy_names: item.therapy_names || (item.therapies ? item.therapies.map((t) => t.name) : []),
    variant_hgvs_descriptions: item.variant_hgvs_descriptions || item.variant_hgvs || [],
    clinical_trial_nct_ids: item.clinical_trial_nct_ids || [],
  });
  return (
    <div className="card-grid">
      {items.map((raw, idx) => {
        const it = normalize(raw);
        return (
          <div className="card evidence-card" key={idx}>
            <div className="card-title">{(it.feature_names && it.feature_names.join?.(", ")) || "—"}</div>
            <div className="muted small strong">{(it.variant_names && it.variant_names.join?.(", ")) || "—"}</div>
            <div className="pill-row">
              <Pill>{it.evidence_type || "—"}</Pill>
              <Pill>{it.evidence_level || "—"}</Pill>
              <Pill>{it.evidence_direction || "—"}</Pill>
              <Pill>{it.evidence_significance || "—"}</Pill>
            </div>
            <div className="kv">
              <span className="label">Disease</span>
              <span>{it.disease_name || "—"}</span>
            </div>
            <div className="kv">
              <span className="label">Therapy</span>
              <span>{(it.therapy_names && it.therapy_names.join?.(", ")) || "—"}</span>
            </div>
            <div className="kv">
              <span className="label">Trials</span>
              <span>{it.clinical_trial_nct_ids.length ? it.clinical_trial_nct_ids.join(", ") : "—"}</span>
            </div>
            <div className="kv">
              <span className="label">Coords</span>
              <span>
                {it.reference_build || "—"} · {it.chromosome || "—"}:{it.start_position || "—"}-{it.stop_position || "—"}
              </span>
            </div>
            <div className="kv">
              <span className="label">HGVS</span>
              <span>{it.variant_hgvs_descriptions.length ? it.variant_hgvs_descriptions.join(", ") : "—"}</span>
            </div>
            <div className="kv">
              <span className="label">CCF / Cohort</span>
              <span>
                {it.cancer_cell_fraction || "—"} / {it.cohort_size || "—"}
              </span>
            </div>
            <div className="kv">
              <span className="label">Source</span>
              <span>
                {it.source_title || "—"} ({it.source_journal || "—"}, {it.source_publication_year || "—"},{" "}
                {it.source_page_numbers || "—"})
              </span>
            </div>
            <div className="quote-block">
              <div className="label tiny">Quote</div>
              <div className="muted tiny ellipsis" title={it.verbatim_quote || ""}>
                “{it.verbatim_quote || "No quote"}”
              </div>
            </div>
            <div className="quote-block">
              <div className="label tiny">Reasoning</div>
              <div className="muted tiny">{it.extraction_reasoning || "No reasoning"}</div>
            </div>
            <div className="muted tiny">
              Confidence:{" "}
              {typeof it.extraction_confidence === "number"
                ? `${Math.round(it.extraction_confidence * 100)}%`
                : it.extraction_confidence || "—"}
            </div>
          </div>
        );
      })}
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

// Phase summaries/details replaced by CheckpointDeck for richer structured view.

function Timeline({ events }) {
  if (!events?.length) return <div className="muted">No timeline events.</div>;
  const recent = events.slice(-200);
  const grouped = recent.reduce((acc, ev) => {
    const key = ev.hook || ev.event || "other";
    acc[key] = acc[key] || [];
    acc[key].push(ev);
    return acc;
  }, {});
  return (
    <div className="timeline">
      {Object.entries(grouped).map(([hook, list]) => (
        <div className="timeline-group" key={hook}>
          <div className="timeline-group-header">
            <span className="pill">{hook}</span>
            <span className="muted small">{list.length} events</span>
                </div>
          {list.map((ev, idx) => (
            <div className="timeline-item" key={`${hook}-${idx}`}>
              <div className="timeline-meta">
                <span className="muted small">{ev.ts}</span>
                <span className="muted tiny">{ev.tool || "—"}</span>
              </div>
              <div className="timeline-body">
                <div className="muted small">input: {ev.input_keys?.join(", ") || "—"}</div>
                {ev.output_summary && <div className="muted small">result: {ev.output_summary}</div>}
                {ev.text && <div className="muted small">msg: {ev.text}</div>}
              </div>
            </div>
          ))}
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

function CheckpointDeck({ phases, pdfUrl, onOpenRaw }) {
  const reader = phases.reader;
  const planner = phases.planner?.plan;
  const extractorItems = phases.extractor?.items || [];
  const critic = phases.critic?.critique;
  const normalizerItems = phases.normalizer?.items || [];

  const topList = (items) => (items || []).slice(0, 3);

  return (
    <div className="deck-grid">
      <div className="card">
        <div className="card-title">Reader (01)</div>
        <div className="muted small">{reader?.content?.title || "—"}</div>
            <div className="muted small">
          {reader?.content?.journal || "—"} · {reader?.content?.year || "—"} · pgs {reader?.content?.num_pages || "—"}
            </div>
        <div className="muted small">Type: {reader?.content?.paper_type || "—"}</div>
            <div className="muted small">
          Sections: {(reader?.content?.sections || []).map((s) => s.name).join(", ") || "—"}
            </div>
        <div className="muted small">
          NCT IDs: {reader?.content?.nct_ids ? JSON.stringify(reader.content.nct_ids) : "—"}
        </div>
        {pdfUrl && (
          <a className="pill link-pill" href={pdfUrl} target="_blank" rel="noreferrer">
            Open PDF
          </a>
        )}
        {onOpenRaw && (
          <button className="pill" onClick={() => onOpenRaw("Reader (01)", phases.reader)}>
            Raw Reader
          </button>
        )}
      </div>

      <div className="card">
        <div className="card-title">Planner (02)</div>
        <div className="muted small">Expected items: {planner?.expected_items ?? "—"}</div>
        <div className="muted small">Key variants: {planner?.key_variants || "—"}</div>
        <div className="muted small">Key therapies: {planner?.key_therapies || "—"}</div>
        <div className="muted small">Key diseases: {planner?.key_diseases || "—"}</div>
        <div className="muted small">Focus sections: {planner?.focus_sections || "—"}</div>
        {onOpenRaw && (
          <button className="pill" onClick={() => onOpenRaw("Planner (02)", phases.planner)}>
            Raw Planner
          </button>
        )}
      </div>

      <div className="card">
        <div className="card-title">Extractor (03)</div>
        <div className="muted small">Draft items: {extractorItems.length}</div>
        <ul className="plain-list small">
          {topList(extractorItems).map((it, idx) => (
            <li key={idx}>
              <strong>{it.feature_names?.join?.(", ") || "—"}</strong> · {it.variant_names?.join?.(", ") || "—"} ·{" "}
              {it.therapy_names?.join?.(", ") || "—"} · {it.disease_name || "—"} ({it.evidence_direction || "—"})
            </li>
          ))}
        </ul>
        {onOpenRaw && (
          <button className="pill" onClick={() => onOpenRaw("Extractor (03)", phases.extractor)}>
            Raw Extractor
          </button>
        )}
      </div>

      <div className="card">
        <div className="card-title">Critic (03b)</div>
        <div className="pill-row">
          <Pill kind={critic?.overall_assessment === "APPROVE" ? "success" : "warning"}>
            {critic?.overall_assessment || "—"}
          </Pill>
        </div>
        <div className="muted small">
          Missing: {critic?.missing_items ? critic.missing_items.length : 0} · Extra:{" "}
          {critic?.extra_items ? critic.extra_items.length : 0}
        </div>
        <div className="muted tiny ellipsis" title={critic?.summary || ""}>
          {critic?.summary || "No summary"}
        </div>
        {onOpenRaw && (
          <button className="pill" onClick={() => onOpenRaw("Critic (03b)", phases.critic)}>
            Raw Critic
          </button>
        )}
      </div>

      <div className="card">
        <div className="card-title">Normalizer (04)</div>
        <div className="muted small">Final items: {normalizerItems.length}</div>
        <ul className="plain-list small">
          {topList(normalizerItems).map((it, idx) => (
            <li key={idx}>
              <strong>{it.feature_names?.join?.(", ") || "—"}</strong> · {it.variant_names?.join?.(", ") || "—"} ·{" "}
              {it.therapy_names?.join?.(", ") || "—"} ({it.evidence_significance || "—"})
            </li>
          ))}
        </ul>
        {onOpenRaw && (
          <button className="pill" onClick={() => onOpenRaw("Normalizer (04)", phases.normalizer)}>
            Raw Normalizer
          </button>
        )}
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

function CheckpointCards({ phases }) {
  const entries = [
    {
      key: "reader",
      title: "Reader (01)",
      summary: phases.reader?.summary,
      detail: phases.reader?.content?.title || "No title",
      meta: phases.reader?.content?.authors,
    },
    {
      key: "planner",
      title: "Planner (02)",
      summary: phases.planner?.summary,
      detail: phases.planner?.plan?.expected_items ? `Expected: ${phases.planner.plan.expected_items}` : "No plan",
      meta: phases.planner?.plan?.key_variants,
    },
    {
      key: "extractor",
      title: "Extractor (03)",
      summary: phases.extractor?.summary,
      detail: phases.extractor?.items ? `Draft items: ${phases.extractor.items.length}` : "No items",
      meta: phases.extractor?.items?.[0]?.disease_name,
    },
    {
      key: "critic",
      title: "Critic (03b)",
      summary: phases.critic?.summary,
      detail: phases.critic?.critique?.overall_assessment || "No critique",
      meta: phases.critic?.critique?.missing_items?.length
        ? `Missing: ${phases.critic.critique.missing_items.length}`
        : "",
    },
    {
      key: "normalizer",
      title: "Normalizer (04)",
      summary: phases.normalizer?.summary,
      detail: phases.normalizer?.items ? `Final items: ${phases.normalizer.items.length}` : "No items",
      meta: phases.normalizer?.items?.[0]?.therapy_names?.join(", "),
    },
  ];

  return (
    <div className="cp-card-grid">
      {entries.map((e) => (
        <div key={e.key} className="card cp-card">
          <div className="card-title">{e.title}</div>
          {e.summary && <div className="muted small">{e.summary}</div>}
          <div className="muted small">{e.detail || "—"}</div>
          {e.meta && <div className="muted tiny">{e.meta}</div>}
        </div>
      ))}
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
  const [allEvidence, setAllEvidence] = useState([]);
  const [graphFilters, setGraphFilters] = useState({
    type: "ALL",
    direction: "ALL",
    search: "",
    diseaseScope: "MM_ONLY",
    minWeight: 0,
  });
  const [graphNode, setGraphNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [jsonModal, setJsonModal] = useState({ open: false, title: "", data: null });
  const [activeTab, setActiveTab] = useState("output");
  const [viewMode, setViewMode] = useState("table");
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState("ALL");
  const [directionFilter, setDirectionFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [pdfStatus, setPdfStatus] = useState({ checked: false, available: false, error: "" });

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
    let canceled = false;
    const loadAll = async () => {
      try {
        const outputs = await Promise.all(
          (papers || [])
            .filter((p) => p.hasOutput)
            .map((p) =>
              fetchJson(`${API_BASE}/api/papers/${p.id}/output`)
                .then((res) => ({ id: p.id, evidence: res?.output?.extraction?.evidence_items || [] }))
                .catch(() => ({ id: p.id, evidence: [] }))
            )
        );
        if (canceled) return;
        const merged = outputs.flatMap((o) =>
          (o.evidence || []).map((ev, idx) => ({
            ...ev,
            __paperId: o.id,
            __evidenceId: `${o.id}__${idx}`,
          }))
        );
        setAllEvidence(merged);
      } catch (err) {
        if (!canceled) setError(err.message);
      }
    };
    if (papers?.length) loadAll();
    return () => {
      canceled = true;
    };
  }, [papers]);

  useEffect(() => {
    let canceled = false;
    if (!selected) return;
    // defer setState to avoid synchronous setState warning
    setTimeout(() => {
      if (canceled) return;
    setLoading(true);
    setError("");
    }, 0);
    Promise.all([
      fetchJson(`${API_BASE}/api/papers/${selected}/output`).catch(() => null),
      fetchJson(`${API_BASE}/api/papers/${selected}/checkpoints`).catch(() => ({ checkpoints: [] })),
      fetchJson(`${API_BASE}/api/papers/${selected}/session`).catch(() => ({ events: [] })),
    ])
      .then(([out, cps, ses]) => {
        if (canceled) return;
        setOutput(out?.output || null);
        const sortedCheckpoints = (cps?.checkpoints || []).slice().sort((a, b) => (a.name || "").localeCompare(b.name || ""));
        setCheckpoints(sortedCheckpoints);
        setPhases(parseCheckpoints(sortedCheckpoints));
        setSessionEvents(ses?.events || []);
      })
      .catch((err) => {
        if (!canceled) setError(err.message);
      })
      .finally(() => {
        if (!canceled) setLoading(false);
      });
    return () => {
      canceled = true;
    };
  }, [selected]);

  const pdfUrl = useMemo(() => {
    if (!selected) return null;
    return `${API_BASE}/api/papers/${selected}/pdf`;
  }, [selected]);

  useEffect(() => {
    let canceled = false;
    if (!pdfUrl) {
      setTimeout(() => {
        if (!canceled) setPdfStatus({ checked: false, available: false, error: "" });
      }, 0);
      return;
    }
    setTimeout(() => {
      if (!canceled) setPdfStatus({ checked: false, available: false, error: "" });
    }, 0);
    fetch(pdfUrl, { method: "HEAD" })
      .then((res) => {
        if (canceled) return;
        setPdfStatus({ checked: true, available: res.ok, error: res.ok ? "" : "PDF not reachable" });
      })
      .catch(() => {
        if (canceled) return;
        setPdfStatus({ checked: true, available: false, error: "PDF not reachable" });
      });
    return () => {
      canceled = true;
    };
  }, [pdfUrl]);

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

  const openJson = (title, data) => setJsonModal({ open: true, title, data });
  const closeJson = () => setJsonModal({ open: false, title: "", data: null });
  const downloadJson = (data, filename) => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  const copyText = (text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text).catch(() => {});
  };

  const paperTitle = phases.reader?.content?.title || output?.paper_info?.title || selected;
  const paperAuthors = phases.reader?.content?.authors || output?.paper_info?.author || "—";
  const paperJournal = phases.reader?.content?.journal || output?.paper_info?.journal || "—";
  const paperYear = phases.reader?.content?.year || output?.paper_info?.year || "—";
  const paperPages = phases.reader?.content?.num_pages || output?.paper_info?.num_pages || "—";
  const paperType = phases.reader?.content?.paper_type || output?.paper_info?.paper_type || "—";
  const currentPaper = papers.find((p) => p.id === selected);
  const evidenceItems = useMemo(() => output?.extraction?.evidence_items || [], [output]);
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
  const graphTypes = Array.from(new Set(allEvidence.map((i) => i.evidence_type).filter(Boolean)));
  const graphDirections = Array.from(new Set(allEvidence.map((i) => i.evidence_direction).filter(Boolean)));
  const groundTruthPath =
    selected && selected.startsWith("PMID_")
      ? `/Users/ali/Downloads/civic/civic_data_analysis/ground_truth/${selected}_ground_truth.json`
      : null;
  const graphEvidence = useMemo(() => {
    const term = graphFilters.search.trim().toLowerCase();
    return (allEvidence || []).filter((item) => {
      const matchesType = graphFilters.type === "ALL" || item.evidence_type === graphFilters.type;
      const matchesDir = graphFilters.direction === "ALL" || item.evidence_direction === graphFilters.direction;
      const matchesDisease =
        graphFilters.diseaseScope === "ALL" ||
        item.disease_efo_id === "EFO_0001378" ||
        item.disease_name?.toLowerCase()?.includes("myeloma");
      const haystack = JSON.stringify(item).toLowerCase();
      const matchesSearch = !term || haystack.includes(term);
      return matchesType && matchesDir && matchesDisease && matchesSearch;
    });
  }, [allEvidence, graphFilters]);

  const calcWeight = (ev) => {
    const levelScores = { A: 1.2, B: 1.0, C: 0.9, D: 0.7, CASE_STUDY: 0.5 };
    const level = levelScores[ev.evidence_level] || 0.4;
    const conf =
      typeof ev.extraction_confidence === "number"
        ? ev.extraction_confidence
        : ev.extraction_confidence === "High"
          ? 0.9
          : 0.6;
    const cohort = ev.cohort_size ? Math.min(Math.log10(ev.cohort_size + 1) / 3, 1) : 0.2;
    return Math.max(0.2, level * (0.5 + conf * 0.4 + cohort * 0.3));
  };

  const significanceColor = (sig) => {
    const s = (sig || "").toLowerCase();
    if (s.includes("resist")) return "#ef4444";
    if (s.includes("response") || s.includes("sensitivity")) return "#22c55e";
    if (s.includes("poor") || s.includes("progress") || s.includes("outcome")) return "#f97316";
    return "#6366f1";
  };

  const graphData = useMemo(() => {
    const nodes = new Map();
    const links = [];
    const addNode = (id, label, kind, meta = {}) => {
      if (!id) return;
      if (!nodes.has(id)) nodes.set(id, { id, label, kind, ...meta });
    };
    graphEvidence.forEach((ev) => {
      const evidId = ev.__evidenceId;
      const diseaseId = ev.disease_efo_id || ev.disease_name || "Disease";
      const outcome = ev.evidence_significance || ev.evidence_type || "Outcome";
      const weight = calcWeight(ev);
      const sigColor = significanceColor(ev.evidence_significance);

      addNode(`claim:${evidId}`, ev.feature_names?.join?.(", ") || "Evidence", "evidence", {
        paper: ev.__paperId,
        weight,
        sig: ev.evidence_significance,
      });
      addNode(`paper:${ev.__paperId}`, ev.__paperId, "paper");
      addNode(`disease:${diseaseId}`, ev.disease_name || diseaseId, "disease");
      (ev.feature_names || []).forEach((g) => addNode(`gene:${g}`, g, "gene"));
      (ev.variant_names || []).forEach((v) => addNode(`alt:${v}`, v, "alteration"));
      (ev.therapy_names || []).forEach((t) => addNode(`tx:${t}`, t, "therapy"));
      addNode(`outcome:${outcome}`, outcome, "outcome");

      links.push({ source: `paper:${ev.__paperId}`, target: `claim:${evidId}`, kind: "SUPPORTS", weight, color: sigColor });
      links.push({ source: `claim:${evidId}`, target: `disease:${diseaseId}`, kind: "ABOUT_DISEASE", weight, color: sigColor });
      (ev.feature_names || []).forEach((g) =>
        links.push({ source: `claim:${evidId}`, target: `gene:${g}`, kind: "ABOUT_BIOMARKER", weight, color: sigColor })
      );
      (ev.variant_names || []).forEach((v) =>
        links.push({ source: `claim:${evidId}`, target: `alt:${v}`, kind: "ABOUT_ALTERATION", weight, color: sigColor })
      );
      (ev.therapy_names || []).forEach((t) =>
        links.push({ source: `claim:${evidId}`, target: `tx:${t}`, kind: "ABOUT_THERAPY", weight, color: sigColor })
      );
      links.push({ source: `claim:${evidId}`, target: `outcome:${outcome}`, kind: "HAS_SIGNIFICANCE", weight, color: sigColor });
    });
    return { nodes: Array.from(nodes.values()), links };
  }, [graphEvidence]);

  const graphDrillEvidence = useMemo(() => {
    if (!graphNode) return [];
    const id = graphNode.id;
    if (id.startsWith("gene:")) {
      const name = id.replace("gene:", "");
      return graphEvidence.filter((ev) => ev.feature_names?.includes(name));
    }
    if (id.startsWith("alt:")) {
      const name = id.replace("alt:", "");
      return graphEvidence.filter((ev) => ev.variant_names?.includes(name));
    }
    if (id.startsWith("tx:")) {
      const name = id.replace("tx:", "");
      return graphEvidence.filter((ev) => ev.therapy_names?.includes(name));
    }
    if (id.startsWith("disease:")) {
      const name = id.replace("disease:", "");
      return graphEvidence.filter((ev) => (ev.disease_efo_id || ev.disease_name) === name);
    }
    if (id.startsWith("outcome:")) {
      const name = id.replace("outcome:", "");
      return graphEvidence.filter((ev) => (ev.evidence_significance || ev.evidence_type) === name);
    }
    if (id.startsWith("claim:")) {
      const evidId = id.replace("claim:", "");
      return graphEvidence.filter((ev) => ev.__evidenceId === evidId);
    }
    return [];
  }, [graphNode, graphEvidence]);
  const exportEvidenceCsv = () => {
    if (!filteredEvidence.length) return;
    const headers = [
      "feature_names",
      "variant_names",
      "variant_origin",
      "disease_name",
      "therapy_names",
      "evidence_type",
      "evidence_level",
      "evidence_direction",
      "evidence_significance",
      "clinical_trial_nct_ids",
      "chromosome",
      "reference_build",
      "start_position",
      "stop_position",
      "variant_hgvs_descriptions",
      "cancer_cell_fraction",
      "cohort_size",
      "source_title",
      "source_publication_year",
      "source_journal",
      "source_page_numbers",
      "verbatim_quote",
      "extraction_confidence",
      "extraction_reasoning",
    ];
    const rows = filteredEvidence.map((item) =>
      headers
        .map((key) => {
          const val = item[key];
          if (Array.isArray(val)) return `"${val.join("; ").replace(/"/g, '""')}"`;
          if (val === undefined || val === null) return "";
          return `"${String(val).replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected || "evidence"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Myeloma Evidence Papers</h2>
        <div className="paper-list">
          {papers.filter((p) => p.id.startsWith("PMID_")).length > 0 && (
            <div className="section-label">CIViC PMIDs (with ground truth)</div>
          )}
          {papers
            .filter((p) => p.id.startsWith("PMID_"))
            .map((p) => (
              <button
                key={p.id}
                className={`paper-btn ${selected === p.id ? "active" : ""}`}
                onClick={() => setSelected(p.id)}
              >
                <div className="paper-title">{p.id.replace("PMID_", "PMID ")}</div>
                <div className="paper-meta">
                  CIViC · {p.hasOutput ? "✅ Output" : "…"} · {p.hasCheckpoints ? "💾 Checkpoints" : "…"}
                </div>
              </button>
            ))}
          {papers.filter((p) => !p.id.startsWith("PMID_")).length > 0 && (
            <div className="section-label">New Papers (beyond CIViC)</div>
          )}
          {papers
            .filter((p) => !p.id.startsWith("PMID_"))
            .map((p) => (
            <button
              key={p.id}
              className={`paper-btn ${selected === p.id ? "active" : ""}`}
              onClick={() => setSelected(p.id)}
            >
              <div className="paper-title">{p.id}</div>
              <div className="paper-meta">
                  New · {p.hasOutput ? "✅ Output" : "…"} · {p.hasCheckpoints ? "💾 Checkpoints" : "…"}
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
            <p className="muted">
              ONCO CITE case study on multiple myeloma papers: CIViC PMIDs show original ground truth; new papers extend
              the set with higher-fidelity extractions. Navigate by paper to view PDF, checkpoints, and final outputs.
            </p>
            <p className="muted small">Pipeline: Reader → Planner → Extractor → Critic → Normalizer</p>
          </div>
          <div className="header-pills">
            {loading && <Pill>Loading…</Pill>}
            {error && <Pill kind="error">{error}</Pill>}
          </div>
        </header>

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
              <button className={`tab-btn ${activeTab === "graph" ? "active" : ""}`} onClick={() => setActiveTab("graph")}>
                Knowledge Graph
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
                      <div className="tag-row">
                        <a className="pill link-pill" href={pdfUrl} target="_blank" rel="noreferrer">
                          Open in new tab
                        </a>
                        <a className="pill" href={pdfUrl} download>
                          Download
                        </a>
                      </div>
                    ) : null
                  }
                />
                {pdfUrl ? (
                  pdfStatus.checked && !pdfStatus.available ? (
                    <div className="muted">
                      PDF not reachable at {pdfUrl}.{" "}
                      <a href={pdfUrl} target="_blank" rel="noreferrer">
                        Try opening directly
                      </a>
                    </div>
                  ) : (
                    <>
                      {currentPaper?.pdfPath && (
                        <div className="muted small">Resolved path: {currentPaper.pdfPath}</div>
                      )}
                      <object className="pdf-embed" data={`${pdfUrl}#view=FitH`} type="application/pdf">
                        <iframe className="pdf-embed" src={pdfUrl} title={selected} />
                        <div className="muted">
                          Inline PDF failed.{" "}
                          <a href={pdfUrl} target="_blank" rel="noreferrer">
                            Open in new tab
                          </a>
                        </div>
                      </object>
                    </>
                  )
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
                      <div className="tag-row">
                        <button className="pill" onClick={() => openJson("Final output JSON", output)}>
                          View JSON
                        </button>
                        <button className="pill" onClick={() => downloadJson(output, `${selected || "final_output"}.json`)}>
                          Download JSON
                        </button>
                      </div>
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
                      {currentPaper?.pdfPath && <div className="muted small">PDF path: {currentPaper.pdfPath}</div>}
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
                      {groundTruthPath && (
                      <div className="muted small">
                          Ground truth: {groundTruthPath}{" "}
                          <button className="pill inline" onClick={() => copyText(groundTruthPath)}>
                            Copy path
                          </button>
                      </div>
                      )}
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
                      <button className="pill" onClick={exportEvidenceCsv} disabled={!filteredEvidence.length}>
                        Export CSV
                      </button>
                      </div>

                    <div className="view-toggle">
                      <button className={`pill ${viewMode === "table" ? "active" : ""}`} onClick={() => setViewMode("table")}>
                        Table
                      </button>
                      <button className={`pill ${viewMode === "cards" ? "active" : ""}`} onClick={() => setViewMode("cards")}>
                        Cards
                      </button>
                    </div>

                    {viewMode === "table" ? <EvidenceTable items={filteredEvidence} /> : <EvidenceCards items={filteredEvidence} />}
                  </>
                ) : (
                  <div className="muted">No final output yet.</div>
                        )}
                      </div>
            )}

            {activeTab === "plan" && (
              <div className="pane">
                <div className="plan-crit-grid">
                  <div className="panel">
                    <SectionHeader title="Plan" />
                    {output?.plan ? <PlanPanel plan={output.plan} /> : <div className="muted">No plan available.</div>}
                    </div>
                  <div className="panel">
                    <SectionHeader title="Critique" />
                    {output?.final_critique ? <CritiquePanel critique={output.final_critique} /> : <div className="muted">No critique available.</div>}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "graph" && (
              <div className="pane">
                <SectionHeader title="Knowledge Graph (all papers)" />
                <div className="filters">
                  <div className="filter-group">
                    <label>Disease scope</label>
                    <select
                      value={graphFilters.diseaseScope}
                      onChange={(e) => setGraphFilters((s) => ({ ...s, diseaseScope: e.target.value }))}
                    >
                      <option value="MM_ONLY">Multiple Myeloma</option>
                      <option value="ALL">All diseases</option>
                    </select>
                  </div>
                  <div className="filter-group">
                    <label>Evidence type</label>
                    <select value={graphFilters.type} onChange={(e) => setGraphFilters((s) => ({ ...s, type: e.target.value }))}>
                      <option value="ALL">All</option>
                      {graphTypes.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="filter-group">
                    <label>Direction</label>
                    <select value={graphFilters.direction} onChange={(e) => setGraphFilters((s) => ({ ...s, direction: e.target.value }))}>
                      <option value="ALL">All</option>
                      {graphDirections.map((d) => (
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
                      value={graphFilters.search}
                      onChange={(e) => setGraphFilters((s) => ({ ...s, search: e.target.value }))}
                      placeholder="Filter nodes/evidence"
                    />
                  </div>
                  <div className="filter-group">
                    <label>Min weight</label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={graphFilters.minWeight}
                      onChange={(e) => setGraphFilters((s) => ({ ...s, minWeight: Number(e.target.value) }))}
                    />
                    <div className="muted tiny">{graphFilters.minWeight.toFixed(1)}</div>
                  </div>
                  <div className="pill muted small">{graphEvidence.length} evidence items</div>
                </div>

                {graphData.nodes.length ? (
                  <div className="graph-grid">
                    <div className="graph-box">
                      <ForceGraph2D
                        graphData={{
                          nodes: graphData.nodes,
                          links: graphData.links.filter((l) => l.weight >= graphFilters.minWeight),
                        }}
                        height={480}
                        nodeLabel={(n) => `${n.label} (${n.kind}${n.paper ? ` · ${n.paper}` : ""})`}
                        nodeAutoColorBy="kind"
                        linkColor={(l) => l.color || "#94a3b8"}
                        linkWidth={(l) => Math.max(1, (l.weight || 0.5) * 3)}
                        onNodeClick={(node) => setGraphNode(node)}
                      />
                    </div>
                    <div className="graph-side">
                      <div className="card">
                        <div className="card-title">Node details</div>
                        {graphNode ? (
                          <>
                            <div className="muted small">Label: {graphNode.label}</div>
                            <div className="muted small">Type: {graphNode.kind}</div>
                            {graphNode.paper && <div className="muted small">Paper: {graphNode.paper}</div>}
                            {graphNode.sig && <div className="muted small">Significance: {graphNode.sig}</div>}
                            {graphNode.weight && (
                              <div className="muted small">Weight: {graphNode.weight.toFixed?.(2) || graphNode.weight}</div>
                            )}
                  </>
                ) : (
                          <div className="muted small">Click a node to drill down.</div>
                )}
              </div>
                      <div className="card">
                        <div className="card-title">Related evidence</div>
                        {graphDrillEvidence.length ? (
                          <div className="drill-list">
                            {graphDrillEvidence.slice(0, 50).map((ev) => (
                              <div key={ev.__evidenceId} className="drill-item">
                                <div className="muted tiny">{ev.__paperId}</div>
                                <div className="muted small strong">{ev.feature_names?.join?.(", ") || "—"}</div>
                                <div className="muted tiny">{ev.variant_names?.join?.(", ") || "—"}</div>
                                <div className="muted tiny">{ev.therapy_names?.join?.(", ") || "—"}</div>
                                <div className="pill-row">
                                  <Pill>{ev.evidence_type || "—"}</Pill>
                                  <Pill>{ev.evidence_direction || "—"}</Pill>
            </div>
                                <div className="muted tiny ellipsis" title={ev.verbatim_quote || ""}>
                                  “{ev.verbatim_quote || "No quote"}”
                                </div>
                            {ev.source_page_numbers && (
                              <div className="muted tiny">Pages: {ev.source_page_numbers}</div>
                            )}
                            {ev.cohort_size && <div className="muted tiny">Cohort: {ev.cohort_size}</div>}
                            {ev.extraction_confidence && (
                              <div className="muted tiny">
                                Confidence:{" "}
                                {typeof ev.extraction_confidence === "number"
                                  ? `${Math.round(ev.extraction_confidence * 100)}%`
                                  : ev.extraction_confidence}
                              </div>
                            )}
                              </div>
                            ))}
                            {graphDrillEvidence.length > 50 && (
                              <div className="muted tiny">Showing 50 of {graphDrillEvidence.length}</div>
                            )}
                          </div>
                        ) : (
                          <div className="muted small">No related evidence.</div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="muted">
                    Knowledge graph is empty. Ensure outputs are available on the API (http://localhost:4177) and reload.
                  </div>
                )}
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
                            Raw {cp.name || `Checkpoint ${idx + 1}`}
                          </button>
                        ))}
              </div>
                    ) : null
                  }
                />
                <CheckpointDeck phases={phases} pdfUrl={pdfUrl} onOpenRaw={(title, data) => openJson(title, data)} />
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
