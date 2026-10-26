import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API = import.meta.env.VITE_API_BASE_URL;

function App() {
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [versions, setVersions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function api(path, options = {}) {
    if (!API) throw new Error("Set VITE_API_BASE_URL in frontend/.env first.");
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  async function refresh() {
    try {
      const data = await api("/files");
      setFiles(data.files || []);
    } catch (e) { setMessage(e.message); }
  }

  useEffect(() => { refresh(); }, []);

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setMessage("For this demo, choose a file smaller than 10 MB.");
      return;
    }
    setBusy(true); setMessage("");
    try {
      const info = await api("/upload-url", {
        method: "POST",
        body: JSON.stringify({
          fileName: file.name, contentType: file.type || "application/octet-stream",
          fileSize: file.size
        })
      });
      const put = await fetch(info.uploadUrl, {
        method: "PUT",
        headers: { "Content-Type": info.contentType },
        body: file
      });
      if (!put.ok) throw new Error("S3 upload failed. Check bucket CORS and the presigned URL.");
      await api("/confirm-upload", {
        method: "POST",
        body: JSON.stringify({
          fileId: info.fileId, s3Key: info.s3Key, fileName: info.fileName,
          contentType: info.contentType, fileSize: info.fileSize
        })
      });
      setMessage("Upload successful.");
      await refresh();
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  async function download(file) {
    try {
      const data = await api(`/download-url?fileId=${encodeURIComponent(file.fileId)}`);
      window.location.href = data.downloadUrl;
    } catch (e) { setMessage(e.message); }
  }

  async function remove(file) {
    if (!window.confirm(`Delete ${file.fileName} from the active file list?`)) return;
    try {
      await api(`/files?fileId=${encodeURIComponent(file.fileId)}`, { method: "DELETE" });
      setMessage("File deleted from the active list.");
      await refresh();
      if (selected?.fileId === file.fileId) { setSelected(null); setVersions([]); }
    } catch (e) { setMessage(e.message); }
  }

  async function showVersions(file) {
    setSelected(file);
    try {
      const data = await api(`/versions?fileId=${encodeURIComponent(file.fileId)}`);
      setVersions(data.versions || []);
    } catch (e) { setMessage(e.message); }
  }

  async function restore(version) {
    if (!selected) return;
    if (!window.confirm("Restore this version as the current file?")) return;
    try {
      await api("/restore", {
        method: "POST",
        body: JSON.stringify({ fileId: selected.fileId, versionId: version.versionId })
      });
      setMessage("Version restored.");
      await refresh();
      await showVersions(selected);
    } catch (e) { setMessage(e.message); }
  }

  function size(bytes = 0) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  return <main className="shell">
    <header className="hero">
      <div className="brand"><div className="logo">☁</div><div><p className="eyebrow">AWS SERVERLESS PROJECT</p><h1>Smart Cloud File Manager</h1><p className="sub">Your files, securely stored in the cloud.</p></div></div>
      <label className={`upload ${busy ? "disabled" : ""}`}>
        {busy ? "Uploading…" : "＋ Upload file"}
        <input type="file" onChange={upload} disabled={busy} />
      </label>
    </header>

    <section className="stats">
      <div className="stat"><span>Active files</span><strong>{files.length}</strong></div>
      <div className="stat"><span>Total storage</span><strong>{size(files.reduce((sum, f) => sum + Number(f.fileSize || 0), 0))}</strong></div>
      <div className="stat"><span>Storage provider</span><strong>Amazon S3</strong></div>
    </section>

    {message && <div className="notice" role="status">{message}<button onClick={() => setMessage("")}>×</button></div>}

    <section className="panel">
      <div className="panel-head"><div><h2>Your files</h2><p>Upload, download, delete, and review previous versions.</p></div><button className="secondary" onClick={refresh}>↻ Refresh</button></div>
      {files.length === 0 ? <div className="empty"><div className="empty-icon">▤</div><h3>No files yet</h3><p>Upload your first file to get started.</p></div> :
        <div className="table-wrap"><table><thead><tr><th>File name</th><th>Size</th><th>Uploaded</th><th>Actions</th></tr></thead>
          <tbody>{files.map(file => <tr key={file.fileId}>
            <td><div className="file-cell"><span className="file-icon">▧</span><span>{file.fileName}</span></div></td>
            <td>{size(Number(file.fileSize || 0))}</td>
            <td>{file.uploadedAt ? new Date(file.uploadedAt).toLocaleString() : "—"}</td>
            <td><div className="actions"><button title="Download" onClick={() => download(file)}>↓</button><button title="Version history" onClick={() => showVersions(file)}>◷</button><button title="Delete" className="danger" onClick={() => remove(file)}>×</button></div></td>
          </tr>)}</tbody>
        </table></div>}
    </section>

    {selected && <section className="panel versions">
      <div className="panel-head"><div><h2>Version history</h2><p>{selected.fileName}</p></div><button className="secondary" onClick={() => {setSelected(null);setVersions([]);}}>Close</button></div>
      {versions.length === 0 ? <p className="muted">No versions found yet. Upload a replacement to the same S3 object key to create additional versions.</p> :
        <div className="version-list">{versions.map((v, i) => <div className="version" key={v.versionId}>
          <div><strong>{v.isLatest ? "Current version" : `Previous version ${i + 1}`}</strong><p>{new Date(v.lastModified).toLocaleString()} · {size(v.size)}</p><code>{v.versionId}</code></div>
          <button className="secondary" onClick={() => restore(v)}>Restore</button>
        </div>)}</div>}
    </section>}
    <footer>Built with Amazon S3 · AWS Lambda · API Gateway · DynamoDB</footer>
  </main>;
}

createRoot(document.getElementById("root")).render(<App />);
