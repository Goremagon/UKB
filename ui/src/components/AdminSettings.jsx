import { useEffect, useState } from "react";
import { DownloadCloud, Shield, UploadCloud, X } from "lucide-react";

import api from "../lib/api";

const tabs = ["Audit Trail", "Maintenance"];

export default function AdminSettings({ onClose }) {
  const [activeTab, setActiveTab] = useState("Audit Trail");
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total_documents: 0, storage_mb: 0, last_backup: null });
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [maintenanceError, setMaintenanceError] = useState("");
  const pageSize = 10;

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const response = await api.get("/admin/audit-logs", {
          params: { page, page_size: pageSize }
        });
        setLogs(response.data.items || []);
        setTotal(response.data.total || 0);
      } catch (err) {
        setLogs([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [page]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get("/admin/stats");
        setStats(response.data);
      } catch (err) {
        setMaintenanceError("Unable to load system stats.");
      }
    };
    fetchStats();
  }, []);

  const handleBackup = async () => {
    setBackupLoading(true);
    setMaintenanceError("");
    try {
      const response = await api.post("/admin/backup", null, { responseType: "blob" });
      const blob = new Blob([response.data], { type: "application/zip" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ukb_system_backup.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setMaintenanceError("Backup download failed.");
    } finally {
      setBackupLoading(false);
    }
  };

  const handleRestore = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setRestoreLoading(true);
    setMaintenanceError("");
    try {
      const formData = new FormData();
      formData.append("backup_file", file);
      await api.post("/admin/restore", formData);
      const response = await api.get("/admin/stats");
      setStats(response.data);
    } catch (err) {
      setMaintenanceError("Restore failed. Please verify the backup file.");
    } finally {
      setRestoreLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-union-200">
            <Shield className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Admin Settings</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4 flex gap-2 border-b border-slate-800 pb-3 text-sm">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-4 py-1.5 ${
                activeTab === tab
                  ? "bg-union-500/20 text-union-200"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === "Audit Trail" && (
          <div className="mt-5">
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Target File</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {loading ? (
                    <tr>
                      <td colSpan="4" className="px-4 py-6 text-center text-slate-400">
                        Loading audit logs...
                      </td>
                    </tr>
                  ) : logs.length === 0 ? (
                    <tr>
                      <td colSpan="4" className="px-4 py-6 text-center text-slate-400">
                        No audit activity recorded yet.
                      </td>
                    </tr>
                  ) : (
                    logs.map((log) => (
                      <tr key={`${log.timestamp}-${log.user}-${log.action}`}>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">{log.user}</td>
                        <td className="px-4 py-3 capitalize">{log.action}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {log.target_file || "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  className="rounded-full border border-slate-700 px-3 py-1 disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  className="rounded-full border border-slate-700 px-3 py-1 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "Maintenance" && (
          <div className="mt-5 space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                <p className="text-xs uppercase text-slate-500">Total Documents</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{stats.total_documents}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                <p className="text-xs uppercase text-slate-500">Storage Used (MB)</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{stats.storage_mb}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                <p className="text-xs uppercase text-slate-500">Last Backup</p>
                <p className="mt-2 text-sm text-slate-300">
                  {stats.last_backup ? new Date(stats.last_backup).toLocaleString() : "Not available"}
                </p>
              </div>
            </div>

            {maintenanceError ? (
              <p className="text-sm text-red-400">{maintenanceError}</p>
            ) : null}

            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <button
                onClick={handleBackup}
                disabled={backupLoading}
                className="flex items-center justify-center gap-2 rounded-lg bg-union-500 px-4 py-2 text-sm font-semibold text-white hover:bg-union-400 disabled:opacity-60"
              >
                <DownloadCloud className="h-4 w-4" />
                {backupLoading ? "Preparing Backup..." : "Download System Backup"}
              </button>

              <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500">
                <UploadCloud className="h-4 w-4" />
                {restoreLoading ? "Restoring..." : "Restore from File"}
                <input
                  type="file"
                  accept="application/zip"
                  onChange={handleRestore}
                  className="hidden"
                  disabled={restoreLoading}
                />
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
