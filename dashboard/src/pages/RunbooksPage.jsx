import { BookOpen, ExternalLink, Search } from 'lucide-react';
import { useState, useEffect } from 'react';
import { RUNBOOKS_DATA } from '../data/mockData';
import { fetchRunbooks } from '../services/api';

export default function RunbooksPage() {
    const [searchQuery, setSearchQuery] = useState('');
    const [runbooks, setRunbooks] = useState(RUNBOOKS_DATA);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const data = await fetchRunbooks();
            if (!cancelled && data && data.length > 0) setRunbooks(data);
        };
        load();
        return () => { cancelled = true; };
    }, []);

    const filtered = runbooks.filter(rb =>
        (rb.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (rb.service || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (rb.content || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div id="runbooks-page">
            <div className="page-header">
                <div>
                    <h1>Runbooks</h1>
                    <p className="page-subtitle">Operational runbooks indexed by Cortex Search for semantic retrieval</p>
                </div>
            </div>

            <div className="filters-bar">
                <div style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px',
                    border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-secondary)', flex: 1, maxWidth: '400px',
                }}>
                    <Search size={14} style={{ color: 'var(--text-tertiary)' }} />
                    <input
                        type="text"
                        placeholder="Search runbooks..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        style={{
                            border: 'none', outline: 'none', background: 'none',
                            fontSize: '13px', color: 'var(--text-primary)', width: '100%',
                        }}
                        id="runbook-search"
                    />
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {filtered.map(rb => (
                    <div key={rb.id} className="card" id={`runbook-${rb.id}`}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <div style={{
                                    width: '32px', height: '32px', borderRadius: 'var(--radius-md)',
                                    background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    <BookOpen size={14} style={{ color: 'var(--text-tertiary)' }} />
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>{rb.title}</div>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '2px' }}>
                                        <span className="body-xs">{rb.id}</span>
                                        <span className="body-xs">· {rb.service}</span>
                                        <span className="body-xs">· Used {rb.matchCount || 0}x by agents</span>
                                    </div>
                                </div>
                            </div>
                            <span className="body-xs">Last used: {rb.lastUsed || 'N/A'}</span>
                        </div>
                        <p className="body-sm" style={{ lineHeight: 1.7, paddingLeft: '42px' }}>{rb.content}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
