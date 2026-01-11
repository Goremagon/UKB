import { useEffect, useMemo, useState } from "react";
import {
  Folder,
  LogOut,
  Lock,
  Search as SearchIcon,
  Settings,
  Shield,
  UploadCloud
} from "lucide-react";

import api from "../lib/api";
import AdminSettings from "./AdminSettings.jsx";
import Upload from "./Upload.jsx";

const docTypes = ["CBA", "Grievance", "Policy", "Arbitration", "Other"];
const departments = ["All", "Operations", "Safety", "HR", "Benefits", "Legal"];

export default function Search({ role, onLogout }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showAdminSettings, setShowAdminSettings] = useState(false);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [docTypeFilters, setDocTypeFilters] = useState({});
  const [department, setDepartment] = useState("All");
  const [dateRange, setDateRange] = useState({ start: "", end: "" });
  const [suggestions, setSuggestions] = useState([]);
  const [pageNumber, setPageNumber] = useState(1);

  const isAdmin = role === "Admin";

  const activeDocTypes = useMemo(
    () => Object.keys(docTypeFilters).filter((key) => docTypeFilters[key]),
    [docTypeFilters]
  );

  useEffect(() => {
    if (!query) {
      setResults([]);
      setSuggestions([]);
      return;
    }
    const delay = setTimeout(async () => {
      try {
        setError("");
        const response = await api.get("/documents/search", {
          params: {
            q: query,
            doc_type: activeDocTypes.length === 1 ? activeDocTypes[0] : undefined,
            department: department !== "All" ? department : undefined,
            start_date: dateRange.start || undefined,
            end_date: dateRange.end || undefined
          }
        });
        setResults(response.data);
        setSelectedDoc(response.data[0] || null);
        const suggestionPool = response.data
          .flatMap((item) => [item.title, item.tags])
          .join(" ")
          .split(/\s+/)
          .filter((word) => word.length > 3);
        setSuggestions([...new Set(suggestionPool)].slice(0, 6));
      } catch (err) {
        setError("Search is temporarily unavailable.");
      }
    }, 350);

    return () => clearTimeout(delay);
  }, [query, activeDocTypes, dateRange, department]);

  const handleExport = async () => {
    if (!query) {
      setError("Enter a search query before exporting.");
      return;
    }
    setExporting(true);
    setError("");
    try {
      const response = await api.get("/documents/export", {
        params: {
          q: query,
          doc_type: activeDocTypes.length === 1 ? activeDocTypes[0] : undefined,
          department: department !== "All" ? department : undefined,
          start_date: dateRange.start || undefined,
          end_date: dateRange.end || undefined
        },
        responseType: "blob"
      });
      const blob = new Blob([response.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ukb_search_export.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const highlight = (snippet) => {
    if (!snippet) return "";
    return snippet
      .replace(/<strong>/g, '<strong class="text-union-200">')
      .replace(/<b>/g, '<strong class="text-union-200">')
      .replace(/<\/b>/g, "</strong>");
  };

  const previewUrl = selectedDoc
    ? `http://localhost:8000/documents/${selectedDoc.doc_id}/preview#page=${pageNumber}`
    : "";

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-900/70 px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-union-200">
            <Shield className="h-7 w-7" />
            <div>
              <h1 className="text-xl font-semibold">Union Knowledge Base</h1>
              <p className="text-xs text-slate-400">Local-only document intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isAdmin && (
              <>
                <button
                  onClick={() => setShowUpload(true)}
                  className="flex items-center gap-2 rounded-lg border border-union-400/40 bg-union-500/10 px-4 py-2 text-sm font-semibold text-union-200 hover:bg-union-500/30"
                >
                  <UploadCloud className="h-4 w-4" />
                  Upload
                </button>
                <button
                  onClick={() => setShowAdminSettings(true)}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500"
                >
                  <Settings className="h-4 w-4" />
                  Admin Settings
                </button>
              </>
            )}
            <button
              onClick={onLogout}
              className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="grid gap-6 px-8 py-6 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="text-sm font-semibold text-slate-200">Filters</h2>
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Doc Type</p>
                <div className="mt-2 space-y-2">
                  {docTypes.map((type) => (
                    <label key={type} className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-union-500"
                        checked={Boolean(docTypeFilters[type])}
                        onChange={(event) =>
                          setDocTypeFilters((prev) => ({
                            ...prev,
                            [type]: event.target.checked
                          }))
                        }
                      />
                      {type}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Department</p>
                <select
                  value={department}
                  onChange={(event) => setDepartment(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                >
                  {departments.map((dept) => (
                    <option key={dept} value={dept}>
                      {dept}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Date Range</p>
                <div className="mt-2 grid gap-2">
                  <input
                    type="date"
                    value={dateRange.start}
                    onChange={(event) =>
                      setDateRange((prev) => ({ ...prev, start: event.target.value }))
                    }
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                  />
                  <input
                    type="date"
                    value={dateRange.end}
                    onChange={(event) =>
                      setDateRange((prev) => ({ ...prev, end: event.target.value }))
                    }
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                  />
                </div>
              </div>
            </div>
          </div>
        </aside>

        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <label className="flex flex-1 items-center gap-3 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
                <SearchIcon className="h-4 w-4 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search contracts, grievances, policies..."
                  className="w-full bg-transparent text-sm focus:outline-none"
                />
              </label>
              <button
                onClick={handleExport}
                disabled={exporting}
                className="rounded-lg border border-union-400/40 bg-union-500/10 px-4 py-2 text-sm font-semibold text-union-200 hover:bg-union-500/30 disabled:opacity-60"
              >
                {exporting ? "Exporting..." : "Export Results to CSV"}
              </button>
            </div>
            {suggestions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setQuery(suggestion)}
                    className="rounded-full border border-slate-700 px-3 py-1 hover:border-union-400 hover:text-union-200"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
          </div>

          <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Folder className="h-4 w-4 text-union-200" />
                Results
              </div>
              <div className="mt-4 space-y-3">
                {results.length === 0 && (
                  <p className="text-sm text-slate-500">No results yet. Try a keyword search.</p>
                )}
                {results.map((item) => (
                  <button
                    key={item.doc_id}
                    onClick={() => setSelectedDoc(item)}
                    className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                      selectedDoc?.doc_id === item.doc_id
                        ? "border-union-400 bg-union-500/10"
                        : "border-slate-800 bg-slate-950/40 hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-slate-100">{item.title}</h3>
                      {isAdmin && item.is_sensitive ? (
                        <span className="flex items-center gap-1 text-xs text-amber-300">
                          <Lock className="h-3.5 w-3.5" />
                          Sensitive
                        </span>
                      ) : null}
                    </div>
                    <p
                      className="mt-2 text-xs text-slate-400"
                      dangerouslySetInnerHTML={{ __html: highlight(item.highlight) }}
                    />
                    {item.tags ? (
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-union-200">
                        {item.tags
                          .split(",")
                          .filter(Boolean)
                          .map((tag) => (
                            <span key={tag} className="rounded-full border border-union-500/40 px-2 py-0.5">
                              {tag}
                            </span>
                          ))}
                      </div>
                    ) : null}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              {selectedDoc ? (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-100">{selectedDoc.title}</h2>
                      <p className="text-xs text-slate-500">Preview the document alongside search hits.</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-300">
                      <label className="text-xs text-slate-400">Jump to page</label>
                      <input
                        type="number"
                        min="1"
                        value={pageNumber}
                        onChange={(event) => setPageNumber(event.target.value)}
                        className="w-20 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-sm"
                      />
                    </div>
                  </div>
                  <div className="mt-4 h-[520px] overflow-hidden rounded-xl border border-slate-800">
                    <iframe
                      title="PDF Preview"
                      src={previewUrl}
                      className="h-full w-full"
                    />
                  </div>
                </>
              ) : (
                <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
                  <p className="text-sm">Select a result to preview the document.</p>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      {showUpload && (
        <Upload
          onClose={() => setShowUpload(false)}
          onSuccess={() => setShowUpload(false)}
        />
      )}
      {showAdminSettings && (
        <AdminSettings onClose={() => setShowAdminSettings(false)} />
      )}
    </div>
  );
}
