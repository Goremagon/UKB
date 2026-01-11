import { useState } from "react";
import { UploadCloud, X } from "lucide-react";

import api from "../lib/api";

const docTypes = ["CBA", "Grievance", "Policy", "Arbitration", "Other"];
const departments = ["Operations", "Safety", "HR", "Benefits", "Legal"];

export default function Upload({ onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [metadata, setMetadata] = useState({
    doc_type: "CBA",
    department: "Operations",
    date_published: "",
    tags: "",
    is_sensitive: false
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleDrop = (event) => {
    event.preventDefault();
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) {
      setFile(dropped);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Please select a PDF to upload.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post("/documents/upload", formData, {
        params: metadata
      });
      if (response.status === 200) {
        onSuccess();
      }
    } catch (err) {
      if (err.response?.status === 409) {
        setError("This document is already in the system.");
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">Upload Document</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div
            onDrop={handleDrop}
            onDragOver={(event) => event.preventDefault()}
            className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/70 px-6 py-8 text-center"
          >
            <UploadCloud className="h-8 w-8 text-union-200" />
            <p className="mt-2 text-sm text-slate-300">
              Drag & drop a PDF or click to choose.
            </p>
            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="mt-3 text-sm text-slate-400"
            />
            {file ? <p className="mt-2 text-xs text-union-200">{file.name}</p> : null}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm text-slate-300">
              Document Type
              <select
                value={metadata.doc_type}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, doc_type: event.target.value }))
                }
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              >
                {docTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-300">
              Department
              <select
                value={metadata.department}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, department: event.target.value }))
                }
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              >
                {departments.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-300">
              Date Published
              <input
                type="date"
                value={metadata.date_published}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, date_published: event.target.value }))
                }
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
            </label>
            <label className="block text-sm text-slate-300">
              Tags
              <input
                type="text"
                placeholder="contract, wage, safety"
                value={metadata.tags}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, tags: event.target.value }))
                }
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={metadata.is_sensitive}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, is_sensitive: event.target.checked }))
                }
                className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-union-500"
              />
              Mark as Sensitive
            </label>
          </div>

          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-union-500 px-4 py-2 text-sm font-semibold text-white hover:bg-union-400 disabled:opacity-60"
            >
              {loading ? "Uploading..." : "Upload Document"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
