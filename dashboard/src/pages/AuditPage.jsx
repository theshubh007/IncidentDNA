import { useState, useEffect, Fragment } from 'react';
import { AUDIT_LOG_DATA } from '../data/mockData';
import { fetchAuditLog } from '../services/api';
import { useApp } from '../hooks/useAppContext';
import { ChevronDown, ChevronRight, Copy } from 'lucide-react';

export default function AuditPage() {
    const { liveActions } = useApp();
    const [expandedRow, setExpandedRow] = useState(null);
    const [statusFilter, setStatusFilter] = useState('all');
    const [toolkitFilter, setToolkitFilter] = useState('all');
    const [apiAudit, setApiAudit] = useState(AUDIT_LOG_DATA);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const data = await fetchAuditLog();
            if (!cancelled) setApiAudit(data);
        };
        load();
        const interval = setInterval(load, 10000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    const allLogs = [
        ...liveActions.map(a => ({
            actionId: a.id,
            decisionId: `DEC-${a.id.split('-')[1]}`,
            toolkit: a.type.includes('SLACK') ? 'composio-slack' : a.type.includes('GITHUB') ? 'composio-github' : 'snowflake',
            actionType: a.type,
            status: a.status,
            retryCount: 0,
            idempotencyKey: `${a.incidentId}:${a.type.toLowerCase()}`,
            timestamp: a.timestamp,
            request: { simulated: true },
            response: { ok: true },
        })),
        ...apiAudit,
    ];

    const toolkits = [...new Set(allLogs.map(l => l.toolkit))];
    const statuses = [...new Set(allLogs.map(l => l.status))];

    const filtered = allLogs.filter(log => {
        if (statusFilter !== 'all' && log.status !== statusFilter) return false;
        if (toolkitFilter !== 'all' && log.toolkit !== toolkitFilter) return false;
        return true;
    });

    return (
        <div id="audit-page">
            <div className="page-header">
                <div>
                    <h1>Audit Log</h1>
                    <p className="page-subtitle">All agent tool calls with request/response receipts, retries & idempotency keys</p>
                </div>
            </div>

            <div className="filters-bar">
                <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)} id="audit-filter-status">
                    <option value="all">All Statuses</option>
                    {statuses.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select className="filter-select" value={toolkitFilter} onChange={e => setToolkitFilter(e.target.value)} id="audit-filter-toolkit">
                    <option value="all">All Toolkits</option>
                    {toolkits.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <span className="body-xs">{filtered.length} entries</span>
            </div>

            <div className="table-container">
                <table className="data-table" id="audit-table">
                    <thead>
                        <tr>
                            <th>Action ID</th>
                            <th>Decision</th>
                            <th>Toolkit</th>
                            <th>Action Type</th>
                            <th>Status</th>
                            <th>Retries</th>
                            <th>Idempotency Key</th>
                            <th>Timestamp</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(log => (
                            <Fragment key={log.actionId}>
                                <tr
                                    className="clickable"
                                    onClick={() => setExpandedRow(expandedRow === log.actionId ? null : log.actionId)}
                                    id={`audit-row-${log.actionId}`}
                                >
                                    <td className="mono-cell">{log.actionId}</td>
                                    <td className="mono-cell">{log.decisionId}</td>
                                    <td style={{ fontSize: '12px' }}>{log.toolkit}</td>
                                    <td style={{ fontSize: '12px' }}>{log.actionType}</td>
                                    <td>
                                        <span className={`status-chip ${log.status}`}>
                                            <span className="chip-dot" />
                                            {log.status}
                                        </span>
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{log.retryCount}</td>
                                    <td>
                                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block', whiteSpace: 'nowrap' }}>
                                            {log.idempotencyKey}
                                        </span>
                                    </td>
                                    <td style={{ fontSize: '12px', color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                                        {new Date(log.timestamp).toLocaleString()}
                                    </td>
                                    <td>
                                        {expandedRow === log.actionId
                                            ? <ChevronDown size={14} style={{ color: 'var(--text-tertiary)' }} />
                                            : <ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} />}
                                    </td>
                                </tr>
                                {expandedRow === log.actionId && (
                                    <tr key={`${log.actionId}-detail`} className="expand-row">
                                        <td colSpan={9}>
                                            <div className="expand-content" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                                <div>
                                                    <div className="label" style={{ marginBottom: '8px' }}>Request Payload</div>
                                                    <pre style={{
                                                        fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.6,
                                                        background: 'var(--bg-secondary)', padding: '12px', borderRadius: 'var(--radius-md)',
                                                        border: '1px solid var(--border-primary)', overflow: 'auto', maxHeight: '200px',
                                                    }}>
                                                        {JSON.stringify(log.request, null, 2)}
                                                    </pre>
                                                </div>
                                                <div>
                                                    <div className="label" style={{ marginBottom: '8px' }}>Response Receipt</div>
                                                    <pre style={{
                                                        fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.6,
                                                        background: 'var(--bg-secondary)', padding: '12px', borderRadius: 'var(--radius-md)',
                                                        border: '1px solid var(--border-primary)', overflow: 'auto', maxHeight: '200px',
                                                    }}>
                                                        {JSON.stringify(log.response, null, 2)}
                                                    </pre>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
