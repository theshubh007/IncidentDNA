import { useState } from 'react';
import { POSTMORTEMS_DATA } from '../data/mockData';
import { FileText, GitBranch, Check, ChevronRight } from 'lucide-react';
import { useApp } from '../hooks/useAppContext';

function PostmortemDoc({ data }) {
    const { addToast } = useApp();
    const pm = data.postmortem;

    return (
        <div className="postmortem-doc">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                <div>
                    <h2>Postmortem — {data.incidentId}</h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                        <span className={`severity-chip ${data.severity}`}>{data.severity}</span>
                        <span className="body-xs">{data.service}</span>
                        <span className="body-xs">· Confidence: {Math.round(data.confidence * 100)}%</span>
                    </div>
                </div>
                <span className="severity-chip healthy">Draft Ready</span>
            </div>

            <h3>Summary</h3>
            <p>{pm.summary}</p>

            <h3>Customer Impact</h3>
            <p>{pm.customerImpact}</p>

            <h3>Root Cause</h3>
            <p>{pm.rootCause}</p>

            <h3>Action Items</h3>
            <div style={{ marginBottom: '24px' }}>
                {pm.actionItems.map((item, i) => (
                    <div key={i} className={`checklist-item${item.done ? ' checked' : ''}`}>
                        <input type="checkbox" checked={item.done} readOnly />
                        <span>{item.text}</span>
                    </div>
                ))}
            </div>

            <div className="section-divider" />

            <div style={{ display: 'flex', gap: '8px' }}>
                <button
                    className="btn btn-primary btn-sm"
                    onClick={() => addToast('GitHub issue created from postmortem', 'success')}
                >
                    <GitBranch size={12} />
                    Create GitHub Issue
                </button>
                <button className="btn btn-secondary btn-sm">
                    Export as Markdown
                </button>
            </div>
        </div>
    );
}

export default function PostmortemsPage() {
    const [selectedId, setSelectedId] = useState(null);
    const selected = POSTMORTEMS_DATA.find(p => p.incidentId === selectedId);

    return (
        <div id="postmortems-page">
            <div className="page-header">
                <div>
                    <h1>Postmortems</h1>
                    <p className="page-subtitle">Auto-drafted incident reports with timelines, impact, and action items</p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: selected ? '320px 1fr' : '1fr', gap: 'var(--space-6)' }}>
                <div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {POSTMORTEMS_DATA.map(pm => (
                            <div
                                key={pm.incidentId}
                                className="card"
                                style={{
                                    cursor: 'pointer',
                                    borderColor: selectedId === pm.incidentId ? 'var(--border-focus)' : undefined,
                                }}
                                onClick={() => setSelectedId(pm.incidentId)}
                                id={`postmortem-${pm.incidentId}`}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>{pm.incidentId}</span>
                                    <span className="severity-chip healthy" style={{ fontSize: '10px' }}>Draft Ready</span>
                                </div>
                                <div className="body-sm" style={{ marginBottom: '6px' }}>{pm.service}</div>
                                <div className="body-xs" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <span className={`severity-chip ${pm.severity}`}>{pm.severity}</span>
                                    <ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {selected && (
                    <PostmortemDoc data={selected} />
                )}
            </div>

            {!selected && POSTMORTEMS_DATA.length > 0 && (
                <div className="empty-state" style={{ marginTop: 'var(--space-8)' }}>
                    <FileText />
                    <h3>Select a postmortem</h3>
                    <p>Click on an incident to view its auto-drafted postmortem report.</p>
                </div>
            )}
        </div>
    );
}
