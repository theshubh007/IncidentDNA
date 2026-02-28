import { useState, useEffect, Fragment } from 'react';
import { RELEASES_DATA } from '../data/mockData';
import { fetchReleases } from '../services/api';
import { ChevronDown, ChevronRight, AlertTriangle, Check, Send, ExternalLink } from 'lucide-react';

function RiskChip({ risk }) {
    return <span className={`risk-chip ${risk}`}>{risk}</span>;
}

function ConfidenceDisplay({ confidence }) {
    const color = confidence >= 80 ? 'var(--color-healthy)' : confidence >= 50 ? 'var(--color-warning)' : 'var(--color-critical)';
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="confidence-bar" style={{ width: '80px' }}>
                <div className="confidence-bar-fill" style={{ width: `${confidence}%`, background: color }} />
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, color }}>{confidence}</span>
        </div>
    );
}

function ReleaseDetail({ release }) {
    return (
        <div className="expand-content" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
                <h4 className="heading-sm" style={{ marginBottom: '12px' }}>Risk Factors</h4>
                {release.riskFactors.length === 0 ? (
                    <p className="body-sm" style={{ color: 'var(--text-tertiary)' }}>No risk factors identified.</p>
                ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {release.riskFactors.map((factor, i) => (
                            <span key={i} style={{
                                display: 'inline-flex', alignItems: 'center', gap: '4px',
                                padding: '4px 10px', background: 'var(--color-warning-bg)', border: '1px solid var(--color-warning-border)',
                                borderRadius: 'var(--radius-full)', fontSize: '12px', color: '#92400e',
                            }}>
                                <AlertTriangle size={10} />
                                {factor}
                            </span>
                        ))}
                    </div>
                )}

                <h4 className="heading-sm" style={{ marginTop: '20px', marginBottom: '12px' }}>Evidence</h4>
                {release.evidence.map((e, i) => (
                    <div key={i} className="evidence-card">
                        <div className="evidence-text">{e}</div>
                    </div>
                ))}
            </div>

            <div>
                <h4 className="heading-sm" style={{ marginBottom: '12px' }}>Recommended Guardrails</h4>
                {release.guardrails.map((g, i) => (
                    <div key={i} className={`checklist-item${g.checked ? ' checked' : ''}`}>
                        <input type="checkbox" checked={g.checked} readOnly />
                        <span>{g.text}</span>
                    </div>
                ))}

                <div style={{ marginTop: '20px' }}>
                    <button className="btn btn-secondary" id={`release-slack-${release.id}`}>
                        <Send size={12} />
                        Post Advisory to Slack
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function ReleasesPage() {
    const [expandedRelease, setExpandedRelease] = useState(null);
    const [releases, setReleases] = useState(RELEASES_DATA);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const data = await fetchReleases();
            if (!cancelled) setReleases(data);
        };
        load();
        const interval = setInterval(load, 15000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    return (
        <div id="releases-page">
            <div className="page-header">
                <div>
                    <h1>Releases</h1>
                    <p className="page-subtitle">Pre-deploy confidence scoring & risk assessment</p>
                </div>
            </div>

            <div className="table-container">
                <table className="data-table" id="releases-table">
                    <thead>
                        <tr>
                            <th>Release</th>
                            <th>Service</th>
                            <th>Version</th>
                            <th>Confidence</th>
                            <th>Risk</th>
                            <th>Author</th>
                            <th>Status</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {releases.map(release => (
                            <Fragment key={release.id}>
                                <tr
                                    className="clickable"
                                    onClick={() => setExpandedRelease(expandedRelease === release.id ? null : release.id)}
                                    id={`release-row-${release.id}`}
                                >
                                    <td className="mono-cell">{release.id}</td>
                                    <td>{release.service}</td>
                                    <td className="mono-cell">{release.version}</td>
                                    <td><ConfidenceDisplay confidence={release.confidence} /></td>
                                    <td><RiskChip risk={release.risk} /></td>
                                    <td style={{ fontSize: '12px' }}>{release.author}</td>
                                    <td>
                                        <span className={`severity-chip ${release.status === 'deployed' ? 'healthy' : 'warning'}`}>
                                            {release.status}
                                        </span>
                                    </td>
                                    <td>
                                        {expandedRelease === release.id ? <ChevronDown size={14} style={{ color: 'var(--text-tertiary)' }} /> : <ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} />}
                                    </td>
                                </tr>
                                {expandedRelease === release.id && (
                                    <tr key={`${release.id}-detail`} className="expand-row">
                                        <td colSpan={8}>
                                            <ReleaseDetail release={release} />
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
