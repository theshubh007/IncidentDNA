import { useState, useEffect } from 'react';
import { SERVICES, SERVICE_SPARKLINES, INCIDENTS_DATA } from '../data/mockData';
import { fetchServices, fetchIncidents } from '../services/api';
import { Activity, ArrowRight, Server, ExternalLink } from 'lucide-react';

function Sparkline({ data, color = 'var(--text-tertiary)', width = 80, height = 24 }) {
    if (!data || data.length === 0) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 4) - 2;
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg width={width} height={height} className="sparkline-container">
            <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

function ServiceCard({ service }) {
    const sparklines = SERVICE_SPARKLINES[service.id];
    const recentIncidents = INCIDENTS_DATA.filter(i => i.service === service.id);
    const statusColor = {
        healthy: 'var(--color-healthy)',
        warning: 'var(--color-warning)',
        critical: 'var(--color-critical)',
    };

    return (
        <div className="card" id={`service-card-${service.id}`} style={{ cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                        width: '36px', height: '36px', borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <Server size={16} style={{ color: 'var(--text-tertiary)' }} />
                    </div>
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>{service.name}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                            {service.dependencies.length} dependencies
                        </div>
                    </div>
                </div>
                <span className={`status-dot ${service.status}`} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                    <div className="label" style={{ marginBottom: '4px' }}>Latency</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600 }}>{service.latency}ms</span>
                        {sparklines && <Sparkline data={sparklines.latency} color="var(--text-tertiary)" />}
                    </div>
                </div>
                <div>
                    <div className="label" style={{ marginBottom: '4px' }}>Error Rate</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600 }}>{(service.errorRate * 100).toFixed(1)}%</span>
                        {sparklines && <Sparkline data={sparklines.errorRate} color={service.errorRate > 0.04 ? 'var(--color-warning)' : 'var(--text-tertiary)'} />}
                    </div>
                </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    Uptime {service.uptime}% · {recentIncidents.length} incidents
                </span>
                <ArrowRight size={14} style={{ color: 'var(--text-tertiary)' }} />
            </div>
        </div>
    );
}

export default function ServicesPage() {
    const [services, setServices] = useState(SERVICES);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const data = await fetchServices();
            if (!cancelled && data && data.length > 0) setServices(data);
        };
        load();
        const interval = setInterval(load, 15000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    return (
        <div id="services-page">
            <div className="page-header">
                <div>
                    <h1>Services</h1>
                    <p className="page-subtitle">Service health, dependencies & performance metrics</p>
                </div>
            </div>

            <div className="grid-3">
                {services.map(service => (
                    <ServiceCard key={service.id} service={service} />
                ))}
            </div>
        </div>
    );
}
