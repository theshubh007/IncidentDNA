import { BookOpen, ExternalLink, Search } from 'lucide-react';
import { useState } from 'react';

const RUNBOOKS = [
    { id: 'RB-001', title: 'DB Pool Tuning Guide', service: 'payment-service', content: 'When connection pool utilization exceeds 80%, increase pool_max by 50%. Monitor for 15 minutes. If issue persists, check for long-running queries using pg_stat_activity.', lastUsed: '2026-02-27', matchCount: 5 },
    { id: 'RB-002', title: 'Rate Limiter Configuration', service: 'api-gateway', content: 'Default rate limit: 1000 req/s per client. To adjust, modify config in consul KV store. Always test in staging first. Rollback: revert consul KV to previous value.', lastUsed: '2026-02-27', matchCount: 3 },
    { id: 'RB-003', title: 'Memory Leak Triage', service: 'all', content: 'Check heap dumps using /debug/pprof. Look for growing allocations over time. Common causes: event listener leaks, unclosed connections, growing caches without TTL.', lastUsed: '2026-02-26', matchCount: 4 },
    { id: 'RB-004', title: 'Redis Failover Recovery', service: 'all', content: 'On Redis cluster failover, expect 10-20 minute cache cold start. Run cache pre-warming script: ./scripts/warm-cache.sh. Monitor hit ratio in Grafana.', lastUsed: '2026-02-25', matchCount: 2 },
    { id: 'RB-005', title: 'Canary Deploy Rollback', service: 'all', content: 'If canary error rate exceeds 5% or P99 latency doubles, trigger automatic rollback. Run: kubectl rollout undo deployment/<service>. Notify #deploys channel.', lastUsed: '2026-02-24', matchCount: 1 },
];

export default function RunbooksPage() {
    const [searchQuery, setSearchQuery] = useState('');

    const filtered = RUNBOOKS.filter(rb =>
        rb.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rb.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rb.content.toLowerCase().includes(searchQuery.toLowerCase())
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
                                        <span className="body-xs">· Used {rb.matchCount}× by agents</span>
                                    </div>
                                </div>
                            </div>
                            <span className="body-xs">Last used: {rb.lastUsed}</span>
                        </div>
                        <p className="body-sm" style={{ lineHeight: 1.7, paddingLeft: '42px' }}>{rb.content}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
