import { useState, useEffect } from 'react';
import { fetchRepoInfo, fetchRepoFeatures } from '../services/api';
import {
    GitBranch, Star, GitFork, ExternalLink, Folder, FileText,
    Clock, Users, Zap, Shield, Brain, Database, MessageSquare,
    Search, Play, Activity, CheckCircle2, ArrowRight
} from 'lucide-react';

const LANG_COLORS = {
    Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6', HTML: '#e34c26',
    CSS: '#563d7c', Shell: '#89e051', Dockerfile: '#384d54', SQL: '#e38c00',
    Makefile: '#427819', SCSS: '#c6538c', Vue: '#41b883', Batchfile: '#c1f12e',
    PowerShell: '#012456',
};

const FEATURE_ICONS = {
    'multi-agent': Brain, 'snowflake-cortex': Database, 'threshold-engine': Shield,
    'composio-actions': MessageSquare, 'incident-dna': Activity, 'demo-mode': Play,
    'vector-search': Search, 'ci-trigger': Zap,
};

export default function RepositoryPage() {
    const [repo, setRepo] = useState(null);
    const [features, setFeatures] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const [r, f] = await Promise.all([fetchRepoInfo(), fetchRepoFeatures()]);
            if (!cancelled) { setRepo(r); setFeatures(f); }
        };
        load();
        const interval = setInterval(load, 60000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    const langs = repo?.languages ? Object.entries(repo.languages).sort((a, b) => b[1] - a[1]) : [];
    const arch = features?.architecture;

    return (
        <div id="repository-page">
            {/* ── Hero: Repo name + stats ── */}
            <div style={{
                padding: '28px 32px 24px', marginBottom: '20px', borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(34,197,94,0.05) 100%)',
                border: '1px solid var(--border-primary)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                    <Shield size={22} style={{ color: 'var(--color-accent)' }} />
                    <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 700, letterSpacing: '-0.5px' }}>
                        {repo?.fullName || 'Loading...'}
                    </h1>
                    {repo?.visibility && (
                        <span style={{
                            padding: '3px 10px', borderRadius: '9999px', fontSize: '11px', fontWeight: 600,
                            background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)', color: '#818cf8',
                        }}>{repo.visibility}</span>
                    )}
                </div>
                <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '600px' }}>
                    {repo?.description || features?.tagline || 'Autonomous Incident Detection, Investigation & Resolution'}
                </p>

                <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
                    {[
                        { icon: Star, val: repo?.stars ?? '-', lbl: 'Stars' },
                        { icon: GitFork, val: repo?.forks ?? '-', lbl: 'Forks' },
                        { icon: GitBranch, val: repo?.defaultBranch ?? 'main', lbl: 'Branch' },
                        { icon: Users, val: repo?.contributors?.length ?? '-', lbl: 'Contributors' },
                    ].map(s => (
                        <div key={s.lbl} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <s.icon size={14} style={{ color: 'var(--text-tertiary)' }} />
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{s.val}</span>
                            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{s.lbl}</span>
                        </div>
                    ))}
                    {repo?.pushedAt && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Clock size={14} style={{ color: 'var(--text-tertiary)' }} />
                            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                                Last push {new Date(repo.pushedAt).toLocaleDateString()}
                            </span>
                        </div>
                    )}
                    {repo?.url && (
                        <a href={repo.url} target="_blank" rel="noopener noreferrer"
                            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 500 }}>
                            <ExternalLink size={12} /> GitHub
                        </a>
                    )}
                </div>

                {/* Language bar inline */}
                {langs.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                        <div style={{ display: 'flex', borderRadius: '4px', overflow: 'hidden', height: '6px', marginBottom: '8px' }}>
                            {langs.map(([lang, pct]) => (
                                <div key={lang} title={`${lang}: ${pct}%`}
                                    style={{ width: `${pct}%`, background: LANG_COLORS[lang] || '#71717a', minWidth: '2px' }} />
                            ))}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                            {langs.map(([lang, pct]) => (
                                <span key={lang} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
                                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: LANG_COLORS[lang] || '#71717a' }} />
                                    <span style={{ fontWeight: 500 }}>{lang}</span>
                                    <span style={{ color: 'var(--text-tertiary)' }}>{pct}%</span>
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* ── Two-column: Features + Architecture ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>

                {/* Platform Features */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Platform Capabilities</span>
                        <span className="body-xs">{features?.features?.length || 0} features</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {(features?.features || []).map(f => {
                            const Icon = FEATURE_ICONS[f.id] || Zap;
                            const isActive = f.status === 'active';
                            return (
                                <div key={f.id} style={{
                                    display: 'flex', alignItems: 'center', gap: '10px',
                                    padding: '8px 12px', borderRadius: '8px', background: 'var(--bg-secondary)',
                                }}>
                                    <Icon size={14} style={{ color: isActive ? 'var(--color-accent)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '1px' }}>{f.title}</div>
                                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {f.stats}
                                        </div>
                                    </div>
                                    <CheckCircle2 size={12} style={{ color: isActive ? '#22c55e' : 'var(--text-tertiary)', opacity: isActive ? 1 : 0.4, flexShrink: 0 }} />
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Architecture + Pipeline */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Architecture</span>
                    </div>
                    {arch && (
                        <>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                                {[
                                    { label: 'AI Agents', value: arch.agents?.join(', '), icon: Brain },
                                    { label: 'Data Store', value: arch.dataStore, icon: Database },
                                    { label: 'LLM Engine', value: arch.llm, icon: Zap },
                                    { label: 'Integrations', value: arch.integrations?.join(', '), icon: MessageSquare },
                                ].map(item => (
                                    <div key={item.label} style={{ padding: '10px 12px', borderRadius: '8px', background: 'var(--bg-secondary)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '4px' }}>
                                            <item.icon size={11} style={{ color: 'var(--color-accent)' }} />
                                            <span style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', letterSpacing: '0.4px' }}>
                                                {item.label}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '12px', fontWeight: 500, lineHeight: 1.3 }}>{item.value}</div>
                                    </div>
                                ))}
                            </div>
                            <div style={{
                                padding: '10px 14px', borderRadius: '8px',
                                background: 'linear-gradient(90deg, rgba(99,102,241,0.05), rgba(34,197,94,0.05))',
                                border: '1px solid var(--border-primary)',
                            }}>
                                <div style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '6px', letterSpacing: '0.4px' }}>
                                    End-to-End Pipeline
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 500 }}>
                                    {(arch.pipeline || '').split(' → ').map((step, i, arr) => (
                                        <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                            <span style={{ padding: '2px 8px', borderRadius: '4px', background: 'var(--bg-primary)', border: '1px solid var(--border-primary)', whiteSpace: 'nowrap' }}>
                                                {step}
                                            </span>
                                            {i < arr.length - 1 && <ArrowRight size={10} style={{ color: 'var(--text-tertiary)' }} />}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                    {!arch && <p className="body-sm" style={{ color: 'var(--text-tertiary)' }}>Loading...</p>}
                </div>
            </div>

            {/* ── Two-column: Files + Commits ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

                {/* File tree */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Repository Structure</span>
                        <span className="body-xs">{repo?.fileTree?.length || 0} items</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        {(repo?.fileTree || []).map(f => {
                            const isDir = f.type === 'dir';
                            return (
                                <div key={f.path} style={{
                                    display: 'flex', alignItems: 'center', gap: '8px',
                                    padding: '5px 10px', borderRadius: '6px', fontSize: '13px', fontFamily: 'var(--font-mono)',
                                }}>
                                    {isDir ? <Folder size={13} style={{ color: '#818cf8', flexShrink: 0 }} /> : <FileText size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />}
                                    <span>{f.name}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Recent commits */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Recent Commits</span>
                        <span className="body-xs">{repo?.recentCommits?.length || 0} latest</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        {(repo?.recentCommits || []).map((c, idx) => (
                            <div key={c.sha + idx} style={{
                                display: 'flex', alignItems: 'center', gap: '10px',
                                padding: '6px 10px', borderRadius: '6px',
                                background: idx % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                            }}>
                                {c.avatar ? (
                                    <img src={c.avatar} alt="" style={{ width: '22px', height: '22px', borderRadius: '50%', flexShrink: 0 }} />
                                ) : (
                                    <Users size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                                )}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '12px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {c.message}
                                    </div>
                                    <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
                                        {c.author} &middot; {c.date ? new Date(c.date).toLocaleDateString() : ''}
                                    </div>
                                </div>
                                <code style={{ fontSize: '10px', color: 'var(--color-accent)', background: 'rgba(99,102,241,0.08)', padding: '2px 6px', borderRadius: '4px', flexShrink: 0 }}>
                                    {c.sha}
                                </code>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
