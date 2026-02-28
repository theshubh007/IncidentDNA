import { useState, useEffect } from 'react';
import { fetchRepoInfo, fetchRepoFeatures } from '../services/api';
import {
    GitBranch, Star, GitFork, ExternalLink, Folder, FileText,
    Clock, Users, Zap, Shield, Brain, Database, MessageSquare,
    Search, Play, Activity, CheckCircle2, ArrowRight, X,
    Link2, ArrowUpRight, Code2
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

/* ── Backdrop + Modal shell ──────────────────────────────────────── */
function Modal({ open, onClose, children, width = '720px' }) {
    if (!open) return null;
    return (
        <div onClick={onClose} style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '24px', animation: 'fadeIn 150ms ease',
        }}>
            <div onClick={e => e.stopPropagation()} style={{
                background: 'var(--bg-primary)', borderRadius: '16px',
                border: '1px solid var(--border-primary)',
                boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
                width: '100%', maxWidth: width, maxHeight: '85vh',
                overflow: 'auto', animation: 'slideUp 200ms ease',
            }}>
                {children}
            </div>
            <style>{`
                @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(12px) } to { opacity: 1; transform: translateY(0) } }
            `}</style>
        </div>
    );
}

/* ── Repo Detail Modal ───────────────────────────────────────────── */
function RepoDetailModal({ repo, open, onClose }) {
    if (!repo) return null;
    const langs = repo.languages ? Object.entries(repo.languages).sort((a, b) => b[1] - a[1]) : [];

    return (
        <Modal open={open} onClose={onClose} width="800px">
            {/* Header */}
            <div style={{
                padding: '24px 28px 20px', borderBottom: '1px solid var(--border-primary)',
                background: 'linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(34,197,94,0.03) 100%)',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                            <div style={{
                                width: '36px', height: '36px', borderRadius: '10px',
                                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                <GitBranch size={18} style={{ color: '#fff' }} />
                            </div>
                            <div>
                                <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, letterSpacing: '-0.3px' }}>{repo.name}</h2>
                                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{repo.fullName}</span>
                            </div>
                            {repo.visibility && (
                                <span style={{
                                    padding: '3px 10px', borderRadius: '9999px', fontSize: '10px', fontWeight: 600,
                                    background: 'rgba(99,102,241,0.1)', color: '#818cf8',
                                }}>{repo.visibility}</span>
                            )}
                        </div>
                        {repo.description && (
                            <p style={{ margin: '8px 0 0', fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '500px' }}>{repo.description}</p>
                        )}
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer', padding: '4px',
                        color: 'var(--text-tertiary)', borderRadius: '6px',
                    }}>
                        <X size={18} />
                    </button>
                </div>

                {/* Stats strip */}
                <div style={{ display: 'flex', gap: '20px', marginTop: '16px', flexWrap: 'wrap' }}>
                    {[
                        { icon: Star, val: repo.stars ?? 0, lbl: 'Stars' },
                        { icon: GitFork, val: repo.forks ?? 0, lbl: 'Forks' },
                        { icon: GitBranch, val: repo.defaultBranch || 'main', lbl: 'Branch' },
                        { icon: Users, val: repo.contributors?.length ?? 0, lbl: 'Contributors' },
                        { icon: FileText, val: repo.fileTree?.length ?? 0, lbl: 'Files' },
                        { icon: Clock, val: repo.pushedAt ? new Date(repo.pushedAt).toLocaleDateString() : '-', lbl: 'Last Push' },
                    ].map(s => (
                        <div key={s.lbl} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                            <s.icon size={12} style={{ color: 'var(--text-tertiary)' }} />
                            <span style={{ fontWeight: 600 }}>{s.val}</span>
                            <span style={{ color: 'var(--text-tertiary)' }}>{s.lbl}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Body */}
            <div style={{ padding: '24px 28px' }}>
                {/* Languages */}
                {langs.length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>Languages</div>
                        <div style={{ display: 'flex', borderRadius: '6px', overflow: 'hidden', height: '8px', marginBottom: '8px' }}>
                            {langs.map(([lang, pct]) => (
                                <div key={lang} title={`${lang}: ${pct}%`}
                                    style={{ width: `${pct}%`, background: LANG_COLORS[lang] || '#71717a', minWidth: '3px' }} />
                            ))}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                            {langs.map(([lang, pct]) => (
                                <span key={lang} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: LANG_COLORS[lang] || '#71717a' }} />
                                    <span style={{ fontWeight: 500 }}>{lang}</span>
                                    <span style={{ color: 'var(--text-tertiary)' }}>{pct}%</span>
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Two-column: Files + Commits */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
                    <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
                            Repository Structure
                        </div>
                        <div style={{
                            padding: '12px', borderRadius: '10px', background: 'var(--bg-secondary)',
                            maxHeight: '240px', overflow: 'auto',
                        }}>
                            {(repo.fileTree || []).map(f => (
                                <div key={f.path} style={{
                                    display: 'flex', alignItems: 'center', gap: '8px',
                                    padding: '4px 6px', fontSize: '12px', fontFamily: 'var(--font-mono)',
                                    borderRadius: '4px',
                                }}>
                                    {f.type === 'dir'
                                        ? <Folder size={13} style={{ color: '#818cf8', flexShrink: 0 }} />
                                        : <FileText size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />}
                                    <span>{f.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
                            Recent Commits
                        </div>
                        <div style={{
                            padding: '12px', borderRadius: '10px', background: 'var(--bg-secondary)',
                            maxHeight: '240px', overflow: 'auto',
                        }}>
                            {(repo.recentCommits || []).map((c, i) => (
                                <div key={c.sha + i} style={{
                                    display: 'flex', alignItems: 'center', gap: '8px',
                                    padding: '5px 6px', fontSize: '12px',
                                }}>
                                    {c.avatar
                                        ? <img src={c.avatar} alt="" style={{ width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0 }} />
                                        : <Users size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.message}</div>
                                        <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{c.author} &middot; {c.date ? new Date(c.date).toLocaleDateString() : ''}</div>
                                    </div>
                                    <code style={{ fontSize: '10px', color: 'var(--color-accent)', background: 'rgba(99,102,241,0.08)', padding: '2px 6px', borderRadius: '4px', flexShrink: 0 }}>{c.sha}</code>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Contributors */}
                {repo.contributors?.length > 0 && (
                    <div style={{ marginBottom: '20px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>Contributors</div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {repo.contributors.map(ct => (
                                <a key={ct.login} href={ct.url} target="_blank" rel="noopener noreferrer"
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '8px',
                                        padding: '6px 12px', borderRadius: '8px', background: 'var(--bg-secondary)',
                                        textDecoration: 'none', fontSize: '12px',
                                        border: '1px solid var(--border-primary)', transition: 'border-color 150ms',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-accent)'}
                                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-primary)'}
                                >
                                    <img src={ct.avatar} alt="" style={{ width: '22px', height: '22px', borderRadius: '50%' }} />
                                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{ct.login}</span>
                                    <span style={{ color: 'var(--text-tertiary)' }}>{ct.contributions} commits</span>
                                </a>
                            ))}
                        </div>
                    </div>
                )}

                <a href={repo.url} target="_blank" rel="noopener noreferrer"
                    style={{
                        display: 'inline-flex', alignItems: 'center', gap: '6px',
                        padding: '8px 16px', borderRadius: '8px',
                        background: 'var(--color-accent)', color: '#fff',
                        textDecoration: 'none', fontWeight: 600, fontSize: '13px',
                        transition: 'opacity 150ms',
                    }}
                    onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
                    onMouseLeave={e => e.currentTarget.style.opacity = '1'}
                >
                    <ExternalLink size={14} /> Open on GitHub
                </a>
            </div>
        </Modal>
    );
}

/* ── Link Repo Form Modal ────────────────────────────────────────── */
function LinkRepoModal({ open, onClose, onLink }) {
    const [url, setUrl] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        // Parse owner/repo from GitHub URL or slug
        let slug = url.trim();
        if (slug.includes('github.com/')) {
            const m = slug.match(/github\.com\/([^/]+\/[^/]+)/);
            if (m) slug = m[1].replace(/\.git$/, '');
        }
        if (!/^[^/]+\/[^/]+$/.test(slug)) {
            setError('Please enter a valid GitHub URL or owner/repo format');
            return;
        }
        onLink(slug);
        setUrl('');
        onClose();
    };

    return (
        <Modal open={open} onClose={onClose} width="480px">
            <div style={{ padding: '28px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                            width: '36px', height: '36px', borderRadius: '10px',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <Link2 size={18} style={{ color: '#fff' }} />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Link Repository</h2>
                            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Connect a GitHub repository to monitor</span>
                        </div>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'var(--text-tertiary)' }}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                        Repository URL or owner/repo
                    </label>
                    <div style={{ position: 'relative', marginBottom: error ? '4px' : '16px' }}>
                        <GitBranch size={14} style={{
                            position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)',
                            color: 'var(--text-tertiary)',
                        }} />
                        <input
                            type="text"
                            value={url}
                            onChange={e => { setUrl(e.target.value); setError(''); }}
                            placeholder="https://github.com/owner/repo or owner/repo"
                            style={{
                                width: '100%', padding: '10px 12px 10px 36px', borderRadius: '10px',
                                border: `1px solid ${error ? '#ef4444' : 'var(--border-primary)'}`,
                                background: 'var(--bg-secondary)', fontSize: '13px',
                                color: 'var(--text-primary)', outline: 'none',
                                transition: 'border-color 150ms',
                                boxSizing: 'border-box',
                            }}
                            onFocus={e => e.target.style.borderColor = error ? '#ef4444' : 'var(--color-accent)'}
                            onBlur={e => e.target.style.borderColor = error ? '#ef4444' : 'var(--border-primary)'}
                            autoFocus
                        />
                    </div>
                    {error && (
                        <p style={{ fontSize: '11px', color: '#ef4444', margin: '0 0 12px 0' }}>{error}</p>
                    )}

                    <div style={{
                        padding: '12px 14px', borderRadius: '8px', background: 'var(--bg-secondary)',
                        marginBottom: '20px', fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: 1.5,
                    }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>What happens next:</div>
                        <div>1. IncidentDNA connects to the repo via Composio</div>
                        <div>2. Push events trigger the autonomous agent pipeline</div>
                        <div>3. Anomalies are detected, investigated & resolved automatically</div>
                    </div>

                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                        <button type="button" onClick={onClose} style={{
                            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border-primary)',
                            background: 'transparent', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
                            color: 'var(--text-secondary)',
                        }}>Cancel</button>
                        <button type="submit" style={{
                            padding: '8px 20px', borderRadius: '8px', border: 'none',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            cursor: 'pointer', fontSize: '13px', fontWeight: 600, color: '#fff',
                            transition: 'opacity 150ms',
                        }}
                            onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
                            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
                        >
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <Link2 size={14} /> Link Repository
                            </span>
                        </button>
                    </div>
                </form>
            </div>
        </Modal>
    );
}

/* ── Repo Card (square block) ────────────────────────────────────── */
function RepoCard({ repo, onClick }) {
    const langs = repo?.languages ? Object.entries(repo.languages).sort((a, b) => b[1] - a[1]) : [];
    const topLangs = langs.slice(0, 3);

    return (
        <div onClick={onClick} style={{
            borderRadius: '14px', border: '1px solid var(--border-primary)',
            background: 'var(--bg-primary)', cursor: 'pointer',
            transition: 'border-color 200ms, box-shadow 200ms, transform 200ms',
            padding: '22px', position: 'relative', overflow: 'hidden',
        }}
            onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--color-accent)';
                e.currentTarget.style.boxShadow = '0 4px 20px rgba(99,102,241,0.12)';
                e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border-primary)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.transform = 'translateY(0)';
            }}
        >
            {/* Status dot */}
            <span style={{
                position: 'absolute', top: '18px', right: '18px',
                width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e',
            }} />

            {/* Icon + Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
                <div style={{
                    width: '40px', height: '40px', borderRadius: '10px',
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.12))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                    <Code2 size={20} style={{ color: 'var(--color-accent)' }} />
                </div>
                <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '-0.2px' }}>{repo.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {repo.fullName}
                    </div>
                </div>
            </div>

            {/* Description */}
            {repo.description && (
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '0 0 14px', lineHeight: 1.4,
                    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {repo.description}
                </p>
            )}

            {/* Language pills */}
            {topLangs.length > 0 && (
                <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap' }}>
                    {topLangs.map(([lang, pct]) => (
                        <span key={lang} style={{
                            display: 'flex', alignItems: 'center', gap: '4px',
                            padding: '3px 8px', borderRadius: '6px', fontSize: '11px',
                            background: 'var(--bg-secondary)',
                        }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: LANG_COLORS[lang] || '#71717a' }} />
                            {lang}
                        </span>
                    ))}
                    {langs.length > 3 && (
                        <span style={{ padding: '3px 8px', borderRadius: '6px', fontSize: '11px', background: 'var(--bg-secondary)', color: 'var(--text-tertiary)' }}>
                            +{langs.length - 3}
                        </span>
                    )}
                </div>
            )}

            {/* Stats row */}
            <div style={{ display: 'flex', gap: '14px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Star size={12} /> {repo.stars ?? 0}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <GitFork size={12} /> {repo.forks ?? 0}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Users size={12} /> {repo.contributors?.length ?? 0}
                </span>
                <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <ArrowUpRight size={12} /> View
                </span>
            </div>
        </div>
    );
}

/* ── Features Panel ──────────────────────────────────────────────── */
function FeaturesPanel({ features }) {
    if (!features) return null;
    const arch = features.architecture;

    return (
        <div className="card" style={{ marginTop: '24px' }}>
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
                    padding: '14px 16px', borderRadius: '10px',
                    background: 'linear-gradient(90deg, rgba(99,102,241,0.05), rgba(34,197,94,0.05))',
                    border: '1px solid var(--border-primary)',
                }}>
                    <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px', letterSpacing: '0.5px' }}>
                        End-to-End Pipeline
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 500 }}>
                        {(arch.pipeline || '').split(' → ').map((step, i, arr) => (
                            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ padding: '3px 10px', borderRadius: '6px', background: 'var(--bg-primary)', border: '1px solid var(--border-primary)', whiteSpace: 'nowrap' }}>{step}</span>
                                {i < arr.length - 1 && <ArrowRight size={10} style={{ color: 'var(--text-tertiary)' }} />}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Main Page ───────────────────────────────────────────────────── */
export default function RepositoryPage() {
    const [repos, setRepos] = useState([]);
    const [features, setFeatures] = useState(null);
    const [selectedRepo, setSelectedRepo] = useState(null);
    const [linkModalOpen, setLinkModalOpen] = useState(false);

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
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1>Repositories</h1>
                    <p className="page-subtitle">Linked repositories monitored by IncidentDNA</p>
                </div>
                <button onClick={() => setLinkModalOpen(true)} style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '8px 16px', borderRadius: '8px', border: 'none',
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    color: '#fff', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                    transition: 'opacity 150ms',
                }}
                    onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
                    onMouseLeave={e => e.currentTarget.style.opacity = '1'}
                >
                    <Link2 size={14} /> Link Repo
                </button>
            </div>

            {/* Repo card grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                {repos.map(repo => (
                    <RepoCard key={repo.fullName} repo={repo} onClick={() => setSelectedRepo(repo)} />
                ))}

                {/* Add repo placeholder card */}
                <div onClick={() => setLinkModalOpen(true)} style={{
                    borderRadius: '14px', border: '2px dashed var(--border-primary)',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '40px 20px', color: 'var(--text-tertiary)', cursor: 'pointer',
                    transition: 'border-color 200ms, color 200ms, transform 200ms', minHeight: '180px',
                }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--color-accent)'; e.currentTarget.style.color = 'var(--color-accent)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-primary)'; e.currentTarget.style.color = 'var(--text-tertiary)'; e.currentTarget.style.transform = 'translateY(0)'; }}
                >
                    <div style={{
                        width: '48px', height: '48px', borderRadius: '12px',
                        background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        marginBottom: '12px',
                    }}>
                        <Link2 size={22} />
                    </div>
                    <span style={{ fontSize: '14px', fontWeight: 600 }}>Link Repository</span>
                    <span style={{ fontSize: '12px', marginTop: '4px' }}>Connect a GitHub repo to monitor</span>
                </div>
            </div>

            {/* Platform features */}
            <FeaturesPanel features={features} />

            {/* Modals */}
            <RepoDetailModal repo={selectedRepo} open={!!selectedRepo} onClose={() => setSelectedRepo(null)} />
            <LinkRepoModal open={linkModalOpen} onClose={() => setLinkModalOpen(false)} onLink={(slug) => console.log('Link repo:', slug)} />
        </div>
    );
}
