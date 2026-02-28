// ═══════════════════════════════════════════════════════════════
// api.js — API Service Layer
//
// This module provides a UNIFIED interface for all data access.
// Every page/component imports from here — NEVER from mockData directly.
//
// HOW TO SWITCH FROM MOCK → REAL DATA:
//   1. Set VITE_USE_LIVE_DATA=true in .env
//   2. Set VITE_API_BASE_URL to your backend URL
//   3. That's it. All components automatically use live data.
//
// Each function:
//   - If live mode: fetches from the FastAPI backend
//   - If mock mode: returns mock data from mockData.js
//   - Handles errors and falls back to mock if API is unreachable
// ═══════════════════════════════════════════════════════════════

import config from '../config';
import {
    INCIDENTS_DATA,
    METRICS_OVERVIEW,
    STEPPER_STATES,
    RELEASES_DATA,
    SERVICES_DATA,
    POSTMORTEMS_DATA,
    AUDIT_LOG_DATA,
    RUNBOOKS_DATA,
    DEPENDENCY_GRAPH,
    SETTINGS_DATA,
    SIMULATION_SCENARIOS,
} from '../data/mockData';

// ── HTTP Client ──────────────────────────────────────────────

const BASE = config.apiBaseUrl;

async function request(endpoint, options = {}) {
    const url = `${BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add auth headers if available
    if (config.composioApiKey) {
        headers['X-Composio-Key'] = config.composioApiKey;
    }

    try {
        const res = await fetch(url, { ...options, headers });
        if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
        return await res.json();
    } catch (err) {
        console.warn(`[API] ${endpoint} failed, using mock:`, err.message);
        return null; // Caller handles fallback
    }
}

// ── Incidents ────────────────────────────────────────────────

export async function fetchIncidents(filters = {}) {
    if (!config.useLiveData) return INCIDENTS_DATA;

    const params = new URLSearchParams(filters).toString();
    const data = await request(`/incidents?${params}`);
    return data ?? INCIDENTS_DATA;
}

export async function fetchIncidentById(id) {
    if (!config.useLiveData) return INCIDENTS_DATA.find(i => i.id === id) || null;

    const data = await request(`/incidents/${id}`);
    return data ?? (INCIDENTS_DATA.find(i => i.id === id) || null);
}

// ── Metrics / Overview ───────────────────────────────────────

export async function fetchMetrics() {
    if (!config.useLiveData) return METRICS_OVERVIEW;

    const data = await request('/metrics/overview');
    return data ?? METRICS_OVERVIEW;
}

export async function fetchStepperState(incidentId) {
    if (!config.useLiveData) return STEPPER_STATES;

    const data = await request(`/incidents/${incidentId}/pipeline`);
    return data ?? STEPPER_STATES;
}

// ── Blast Radius / Dependency Graph ──────────────────────────

export async function fetchDependencyGraph(serviceId) {
    if (!config.useLiveData) return DEPENDENCY_GRAPH;

    const data = await request(`/services/${serviceId}/dependencies`);
    return data ?? DEPENDENCY_GRAPH;
}

// ── Releases ─────────────────────────────────────────────────

export async function fetchReleases() {
    if (!config.useLiveData) return RELEASES_DATA;

    const data = await request('/releases');
    return data ?? RELEASES_DATA;
}

export async function fetchReleaseConfidence(releaseId) {
    if (!config.useLiveData) {
        const r = RELEASES_DATA.find(r => r.id === releaseId);
        return r ? { confidence: r.confidence, risk: r.risk, riskFactors: r.riskFactors } : null;
    }

    const data = await request(`/releases/${releaseId}/confidence`);
    return data;
}

// ── Services ─────────────────────────────────────────────────

export async function fetchServices() {
    if (!config.useLiveData) return SERVICES_DATA;

    const data = await request('/services');
    return data ?? SERVICES_DATA;
}

// ── Postmortems ──────────────────────────────────────────────

export async function fetchPostmortems() {
    if (!config.useLiveData) return POSTMORTEMS_DATA;

    const data = await request('/postmortems');
    return data ?? POSTMORTEMS_DATA;
}

export async function fetchPostmortemById(id) {
    if (!config.useLiveData) return POSTMORTEMS_DATA.find(p => p.id === id) || null;

    const data = await request(`/postmortems/${id}`);
    return data ?? (POSTMORTEMS_DATA.find(p => p.id === id) || null);
}

// ── Audit Log ────────────────────────────────────────────────

export async function fetchAuditLog(filters = {}) {
    if (!config.useLiveData) return AUDIT_LOG_DATA;

    const params = new URLSearchParams(filters).toString();
    const data = await request(`/audit?${params}`);
    return data ?? AUDIT_LOG_DATA;
}

// ── Runbooks ─────────────────────────────────────────────────

export async function fetchRunbooks() {
    if (!config.useLiveData) return RUNBOOKS_DATA;

    const data = await request('/runbooks');
    return data ?? RUNBOOKS_DATA;
}

// ── Settings ─────────────────────────────────────────────────

export async function fetchSettings() {
    if (!config.useLiveData) return SETTINGS_DATA;

    const data = await request('/settings');
    return data ?? SETTINGS_DATA;
}

export async function updateSettings(settings) {
    if (!config.useLiveData) {
        console.log('[Mock] Settings updated:', settings);
        return { success: true };
    }

    return await request('/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
    });
}

// ── Simulation ───────────────────────────────────────────────

export async function fetchSimulationScenarios() {
    if (!config.useLiveData) return SIMULATION_SCENARIOS;

    const data = await request('/simulation/scenarios');
    return data ?? SIMULATION_SCENARIOS;
}

export async function runSimulation(scenarioId) {
    if (!config.useLiveData) {
        // Return a mock event stream
        return {
            id: `SIM-${Date.now()}`,
            scenario: scenarioId,
            status: 'running',
        };
    }

    return await request('/simulation/run', {
        method: 'POST',
        body: JSON.stringify({ scenarioId }),
    });
}

// ── CrewAI Agent ─────────────────────────────────────────────

export async function triggerAgent(input) {
    if (!config.useLiveData) {
        console.log('[Mock] Agent triggered:', input);
        return { status: 'simulated', decisions: [] };
    }

    try {
        const res = await fetch(config.crewaiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(config.crewaiApiKey ? { 'Authorization': `Bearer ${config.crewaiApiKey}` } : {}),
            },
            body: JSON.stringify(input),
        });
        return await res.json();
    } catch (err) {
        console.error('[CrewAI] Agent call failed:', err.message);
        return { status: 'error', message: err.message };
    }
}

// ── WebSocket (Real-time Events) ─────────────────────────────

let ws = null;

export function connectRealtime(onEvent) {
    if (!config.enableRealtime) {
        console.log('[WS] Real-time disabled, skipping connection');
        return () => { };
    }

    ws = new WebSocket(config.wsUrl);

    ws.onopen = () => console.log('[WS] Connected to', config.wsUrl);
    ws.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            onEvent(data);
        } catch (e) {
            console.warn('[WS] Invalid message:', e);
        }
    };
    ws.onerror = (err) => console.error('[WS] Error:', err);
    ws.onclose = () => {
        console.log('[WS] Disconnected, reconnecting in 3s...');
        setTimeout(() => connectRealtime(onEvent), 3000);
    };

    // Return cleanup function
    return () => {
        if (ws) ws.close();
        ws = null;
    };
}

// ── Composio Tool Calls (Slack / GitHub) ─────────────────────

export async function sendSlackAlert(channel, message) {
    if (!config.useLiveData) {
        console.log(`[Mock] Slack → #${channel}:`, message);
        return { ok: true, ts: Date.now() };
    }

    return await request('/tools/slack/send', {
        method: 'POST',
        body: JSON.stringify({
            connectionId: config.composioSlackId,
            channel,
            message,
        }),
    });
}

export async function createGitHubIssue(repo, title, body) {
    if (!config.useLiveData) {
        console.log(`[Mock] GitHub issue → ${repo}:`, title);
        return { ok: true, issueNumber: Math.floor(Math.random() * 1000) };
    }

    return await request('/tools/github/issue', {
        method: 'POST',
        body: JSON.stringify({
            connectionId: config.composioGithubId,
            repo,
            title,
            body,
        }),
    });
}

// ── Repository Info ──────────────────────────────────────────

export async function fetchRepoInfo() {
    // Always try — this uses Composio GitHub API, not Snowflake
    const data = await request('/repo');
    return data;
}

export async function fetchRepoFeatures() {
    if (!config.useLiveData) return null;

    const data = await request('/repo/features');
    return data;
}

// ── MTTR Analytics ───────────────────────────────────────────

export async function fetchMTTR() {
    if (!config.useLiveData) return [];

    const data = await request('/metrics/mttr');
    return data ?? [];
}

// ── Metric Deviations ───────────────────────────────────────

export async function fetchDeviations() {
    if (!config.useLiveData) return [];

    const data = await request('/metrics/deviations');
    return data ?? [];
}

// ── Blast Radius ────────────────────────────────────────────

export async function fetchBlastRadius() {
    if (!config.useLiveData) return [];

    const data = await request('/metrics/blast-radius');
    return data ?? [];
}

// ── Reasoning Trace ─────────────────────────────────────────

export async function fetchReasoning(eventId) {
    if (!config.useLiveData) return [];

    const data = await request(`/reasoning/${eventId}`);
    return data ?? [];
}

// ── Slack Sentiment ─────────────────────────────────────────

export async function fetchSentiment() {
    if (!config.useLiveData) return [];

    const data = await request('/metrics/sentiment');
    return data ?? [];
}

// ── Snowflake Queries ────────────────────────────────────────

export async function querySnowflake(sql) {
    if (!config.useLiveData) {
        console.log('[Mock] Snowflake query:', sql);
        return { rows: [], columns: [] };
    }

    return await request('/snowflake/query', {
        method: 'POST',
        body: JSON.stringify({
            sql,
            warehouse: config.snowflakeWarehouse,
            database: config.snowflakeDatabase,
        }),
    });
}
