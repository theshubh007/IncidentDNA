import { useState, useEffect } from 'react';
import { fetchRepoInfo, fetchRepoFeatures } from '../services/api';
import {
    GitBranch, Star, GitFork, ExternalLink, Folder, FileText,
    Clock, Users, Zap, Shield, Brain, Database, MessageSquare,
    Search, Play, Activity, CheckCircle2, ArrowRight, ChevronDown,
    ChevronRight, Plus, Link2
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

function RepoCard({ repo, isExpanded, onToggle }) {
    const langs = repo?.languages ? Object.entries(repo.languages).sort((a, b) => b[1] - a[1]) : [];
    const topLang = langs[0]?.[0] || 'N/A';

    return (
        <div style={{
            borderRadius: '12px', border: '1px solid var(--border-primary)',
            background: 'var(--bg-primary)', overflow: 'hidden',
            transition: 'border-color 150ms, box-shadow 150ms',
            borderColor: isExpanded ? 'var(--color-accent)' : 'var(--border-primary)',
            boxShadow: isExpanded ? '0 0 0 1px rgba(99,102,241,0.1)' : 'none',
        }}>
            {/* Card header — always visible */}
            <div onClick={onToggle} style={{
                padding: '20px', cursor: 'pointer',
                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
            }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <GitBranch size={18} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
                        <span style={{ fontSize: '15px', fontWeight: 700 }}>{repo.name}</span>
                        {repo.visibility && (
                            <span style={{
                                padding: '2px 8px', borderRadius: '9999px', fontSize: '10px', fontWeight: 600,
                                background: 'rgba(99,102,241,0.1)', color: '#818cf8',
                            }}>{repo.visibility}</span>
                        )}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {repo.fullName}
                    </div>
                    <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Star size={12} /> {repo.stars ?? 0}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <GitFork size={12} /> {repo.forks ?? 0}
                        </span>
                        <span>{topLang}</span>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                        width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e', flexShrink: 0,
                    }} />
                    {isExpanded ? <ChevronDown size={16} style={{ color: 'var(--text-tertiary)' }} /> : <ChevronRight size={16} style={{ color: 'var(--text-tertiary)' }} />}
                </div>
            </div>

            {/* Expanded details */}
            {isExpanded && (
                <div style={{ borderTop: '1px solid var(--border-primary)', padding: '20px' }}>
                    {/* Description */}
                    {repo.description && (
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>{repo.description}</p>
                    )}

                    {/* Stats row */}
                    <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
                        {[
                            { icon: GitBranch, val: repo.defaultBranch || 'main', lbl: 'Branch' },
                            { icon: Users, val: repo.contributors?.length ?? 0, lbl: 'Contributors' },
                            { icon: Clock, val: repo.pushedAt ? new Date(repo.pushedAt).toLocaleDateString() : '-', lbl: 'Last Push' },
                            { icon: FileText, val: repo.fileTree?.length ?? 0, lbl: 'Files' },
                        ].map(s => (
                            <div key={s.lbl} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                                <s.icon size={12} style={{ color: 'var(--text-tertiary)' }} />
                                <span style={{ fontWeight: 600 }}>{s.val}</span>
                                <span style={{ color: 'var(--text-tertiary)' }}>{s.lbl}</span>
                            </div>
                        ))}
                    </div>

                    {/* Language bar */}
                    {langs.length > 0 && (
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.4px' }}>Languages</div>
                            <div style={{ display: 'flex', borderRadius: '4px', overflow: 'hidden', height: '6px', marginBottom: '6px' }}>
                                {langs.map(([lang, pct]) => (
                                    <div key={lang} title={`${lang}: ${pct}%`}
                                        style={{ width: `${pct}%`, background: LANG_COLORS[lang] || '#71717a', minWidth: '2px' }} />
                                ))}
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {langs.map(([lang, pct]) => (
                                    <span key={lang} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: LANG_COLORS[lang] || '#71717a' }} />
                                        <span style={{ fontWeight: 500 }}>{lang}</span>
                                        <span style={{ color: 'var(--text-tertiary)' }}>{pct}%</span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Two-column: Files + Commits */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                        <div>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.4px' }}>
                                Structure ({repo.fileTree?.length || 0} items)
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', maxHeight: '200px', overflow: 'auto' }}>
                                {(repo.fileTree || []).map(f => (
                                    <div key={f.path} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                                        {f.type === 'dir' ? <Folder size={12} style={{ color: '#818cf8' }} /> : <FileText size={12} style={{ color: 'var(--text-tertiary)' }} />}
                                        <span>{f.name}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.4px' }}>
                                Recent Commits
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '200px', overflow: 'auto' }}>
                                {(repo.recentCommits || []).slice(0, 5).map((c, i) => (
                                    <div key={c.sha + i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                                        {c.avatar ? <img src={c.avatar} alt="" style={{ width: '18px', height: '18px', borderRadius: '50%' }} /> : <Users size={12} style={{ color: 'var(--text-tertiary)' }} />}
                                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.message}</span>
                                        <code style={{ fontSize: '10px', color: 'var(--color-accent)', background: 'rgba(99,102,241,0.08)', padding: '1px 5px', borderRadius: '3px', flexShrink: 0 }}>{c.sha}</code>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Contributors */}
                    {repo.contributors?.length > 0 && (
                        <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.4px' }}>Contributors</div>
                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                {repo.contributors.map(ct => (
                                    <a key={ct.login} href={ct.url} target="_blank" rel="noopener noreferrer" title={`${ct.login} (${ct.contributions} commits)`}
                                        style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '6px', background: 'var(--bg-secondary)', textDecoration: 'none', fontSize: '12px' }}>
                                        <img src={ct.avatar} alt="" style={{ width: '18px', height: '18px', borderRadius: '50%' }} />
                                        <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{ct.login}</span>
                                        <span style={{ color: 'var(--text-tertiary)', fontSize: '11px' }}>{ct.contributions}</span>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    <a href={repo.url} target="_blank" rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 600 }}>
                        <ExternalLink size={12} /> View on GitHub
                    </a>
                </div>
            )}
        </div>
    );
}

function FeaturesPanel({ features }) {
    if (!features) return null;
    const arch = features.architecture;

    return (
        <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
                <span className="card-title">Platform Capabilities</span>
                <span className="body-xs">{features.features?.length || 0} features</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px', marginBottom: '16px' }}>
                {(features.features || []).map(f => {
                    const Icon = FEATURE_ICONS[f.id] || Zap;
                    const isActive = f.status === 'active';
                    return (
                        <div key={f.id} style={{
                            display: 'flex', alignItems: 'center', gap: '10px',
                            padding: '10px 12px', borderRadius: '8px', background: 'var(--bg-secondary)',
                        }}>
                            <Icon size={14} style={{ color: isActive ? 'var(--color-accent)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: '12px', fontWeight: 600 }}>{f.title}</div>
                                <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.stats}</div>
                            </div>
                            <CheckCircle2 size={12} style={{ color: isActive ? '#22c55e' : 'var(--text-tertiary)', opacity: isActive ? 1 : 0.4, flexShrink: 0 }} />
                        </div>
                    );
                })}
            </div>
            {arch && (
                <div style={{
                    padding: '12px 16px', borderRadius: '8px',
                    background: 'linear-gradient(90deg, rgba(99,102,241,0.05), rgba(34,197,94,0.05))',
                    border: '1px solid var(--border-primary)',
                }}>
                    <div style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '6px', letterSpacing: '0.4px' }}>
                        End-to-End Pipeline
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 500 }}>
                        {(arch.pipeline || '').split(' → ').map((step, i, arr) => (
                            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ padding: '2px 8px', borderRadius: '4px', background: 'var(--bg-primary)', border: '1px solid var(--border-primary)', whiteSpace: 'nowrap' }}>{step}</span>
                                {i < arr.length - 1 && <ArrowRight size={10} style={{ color: 'var(--text-tertiary)' }} />}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function RepositoryPage() {
    const [repos, setRepos] = useState([]);
    const [features, setFeatures] = useState(null);
    const [expandedRepo, setExpandedRepo] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const [r, f] = await Promise.all([fetchRepoInfo(), fetchRepoFeatures()]);
            if (!cancelled) {
                if (r) setRepos([r]);
                setFeatures(f);
            }
        };
        load();
        const interval = setInterval(load, 60000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    return (
        <div id="repository-page">
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>Repositories</h1>
                    <p className="page-subtitle">Linked repositories monitored by IncidentDNA</p>
                </div>
            </div>

            {/* Repo cards grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
                {repos.map(repo => (
                    <RepoCard
                        key={repo.fullName}
                        repo={repo}
                        isExpanded={expandedRepo === repo.fullName}
                        onToggle={() => setExpandedRepo(expandedRepo === repo.fullName ? null : repo.fullName)}
                    />
                ))}

                {/* Add repo placeholder */}
                <div style={{
                    borderRadius: '12px', border: '2px dashed var(--border-primary)',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '40px 20px', color: 'var(--text-tertiary)', cursor: 'pointer',
                    transition: 'border-color 150ms, color 150ms', minHeight: '140px',
                }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--color-accent)'; e.currentTarget.style.color = 'var(--color-accent)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-primary)'; e.currentTarget.style.color = 'var(--text-tertiary)'; }}
                >
                    <Link2 size={24} style={{ marginBottom: '8px' }} />
                    <span style={{ fontSize: '13px', fontWeight: 600 }}>Link Repository</span>
                    <span style={{ fontSize: '11px', marginTop: '4px' }}>Connect a GitHub repo to monitor</span>
                </div>
            </div>

            {/* Platform features below */}
            <FeaturesPanel features={features} />
        </div>
    );
}
