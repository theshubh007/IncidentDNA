// ═══════════════════════════════════════════════════════════════
// Page Tests — Releases, Services, Postmortems, Audit, Settings
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/helpers';
import ReleasesPage from './ReleasesPage';
import ServicesPage from './ServicesPage';
import PostmortemsPage from './PostmortemsPage';
import AuditPage from './AuditPage';
import SettingsPage from './SettingsPage';
import RunbooksPage from './RunbooksPage';

// ── Releases ──────────────────────────────────────────────────
describe('Releases Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<ReleasesPage />);
        expect(screen.getByText('Releases')).toBeInTheDocument();
    });

    it('renders subtitle with confidence info', () => {
        renderWithProviders(<ReleasesPage />);
        expect(screen.getByText(/Pre-deploy confidence/)).toBeInTheDocument();
    });

    it('renders the releases table', () => {
        renderWithProviders(<ReleasesPage />);
        expect(document.getElementById('releases-table')).toBeInTheDocument();
    });

    it('renders release rows', () => {
        renderWithProviders(<ReleasesPage />);
        expect(screen.getByText('REL-042')).toBeInTheDocument();
        expect(screen.getByText('REL-041')).toBeInTheDocument();
    });

    it('clicking a row expands details', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ReleasesPage />);

        const row = document.getElementById('release-row-REL-042');
        await user.click(row);

        // Risk factors should appear
        expect(screen.getByText('Friday deploy')).toBeInTheDocument();
        expect(screen.getByText('Touches DB schema')).toBeInTheDocument();
    });

    it('shows guardrails checklist in expanded view', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ReleasesPage />);

        await user.click(document.getElementById('release-row-REL-042'));

        expect(screen.getByText('Recommended Guardrails')).toBeInTheDocument();
        expect(screen.getByText('Run connection pool load test')).toBeInTheDocument();
    });

    it('shows Slack advisory button', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ReleasesPage />);

        await user.click(document.getElementById('release-row-REL-042'));

        expect(screen.getByText('Post Advisory to Slack')).toBeInTheDocument();
    });
});

// ── Services ──────────────────────────────────────────────────
describe('Services Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<ServicesPage />);
        expect(screen.getByText('Services')).toBeInTheDocument();
    });

    it('renders all service cards', () => {
        renderWithProviders(<ServicesPage />);
        expect(screen.getByText('llm-gateway')).toBeInTheDocument();
        expect(screen.getByText('api-gateway')).toBeInTheDocument();
        expect(screen.getByText('auth-service')).toBeInTheDocument();
        expect(screen.getByText('alert-engine')).toBeInTheDocument();
        expect(screen.getByText('threat-analyzer')).toBeInTheDocument();
        expect(screen.getByText('model-registry')).toBeInTheDocument();
    });

    it('each service card has unique ID', () => {
        renderWithProviders(<ServicesPage />);
        expect(document.getElementById('service-card-llm-gateway')).toBeInTheDocument();
        expect(document.getElementById('service-card-api-gateway')).toBeInTheDocument();
    });

    it('renders latency and error rate labels', () => {
        renderWithProviders(<ServicesPage />);
        const latencyLabels = screen.getAllByText('Latency');
        expect(latencyLabels.length).toBeGreaterThanOrEqual(1);
    });
});

// ── Postmortems ───────────────────────────────────────────────
describe('Postmortems Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<PostmortemsPage />);
        expect(screen.getByText('Postmortems')).toBeInTheDocument();
    });

    it('shows postmortem cards', () => {
        renderWithProviders(<PostmortemsPage />);
        expect(screen.getByText('INC-001')).toBeInTheDocument();
    });

    it('shows empty state prompt before selection', () => {
        renderWithProviders(<PostmortemsPage />);
        expect(screen.getByText('Select a postmortem')).toBeInTheDocument();
    });

    it('clicking a postmortem shows the doc view', async () => {
        const user = userEvent.setup();
        renderWithProviders(<PostmortemsPage />);

        await user.click(document.getElementById('postmortem-INC-001'));

        expect(screen.getByText('Summary')).toBeInTheDocument();
        expect(screen.getByText('Customer Impact')).toBeInTheDocument();
        expect(screen.getByText('Root Cause')).toBeInTheDocument();
        expect(screen.getByText('Action Items')).toBeInTheDocument();
    });

    it('shows Create GitHub Issue button in doc view', async () => {
        const user = userEvent.setup();
        renderWithProviders(<PostmortemsPage />);

        await user.click(document.getElementById('postmortem-INC-001'));

        expect(screen.getByText('Create GitHub Issue')).toBeInTheDocument();
    });
});

// ── Audit Log ─────────────────────────────────────────────────
describe('Audit Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<AuditPage />);
        expect(screen.getByText('Audit Log')).toBeInTheDocument();
    });

    it('renders the audit table', () => {
        renderWithProviders(<AuditPage />);
        expect(document.getElementById('audit-table')).toBeInTheDocument();
    });

    it('renders filter dropdowns', () => {
        renderWithProviders(<AuditPage />);
        expect(document.getElementById('audit-filter-status')).toBeInTheDocument();
        expect(document.getElementById('audit-filter-toolkit')).toBeInTheDocument();
    });

    it('shows audit entries with action IDs', () => {
        renderWithProviders(<AuditPage />);
        expect(screen.getByText('ACT-001')).toBeInTheDocument();
        expect(screen.getByText('ACT-002')).toBeInTheDocument();
    });

    it('clicking a row expands to show request/response', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AuditPage />);

        await user.click(document.getElementById('audit-row-ACT-001'));

        expect(screen.getByText('Request Payload')).toBeInTheDocument();
        expect(screen.getByText('Response Receipt')).toBeInTheDocument();
    });

    it('shows idempotency keys', () => {
        renderWithProviders(<AuditPage />);
        expect(screen.getByText(/INC-001:slack:alert/)).toBeInTheDocument();
    });
});

// ── Settings ──────────────────────────────────────────────────
describe('Settings Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<SettingsPage />);
        expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('renders Tool Connections section', () => {
        renderWithProviders(<SettingsPage />);
        expect(screen.getByText('Tool Connections')).toBeInTheDocument();
    });

    it('renders Agent Policies section', () => {
        renderWithProviders(<SettingsPage />);
        expect(screen.getByText('Agent Policies')).toBeInTheDocument();
    });

    it('shows all connections', () => {
        renderWithProviders(<SettingsPage />);
        expect(screen.getByText('Snowflake')).toBeInTheDocument();
        expect(screen.getByText('GitHub (Composio)')).toBeInTheDocument();
        expect(screen.getByText('Slack (Composio)')).toBeInTheDocument();
        expect(screen.getByText('CrewAI Engine')).toBeInTheDocument();
    });

    it('all connections show as connected', () => {
        renderWithProviders(<SettingsPage />);
        const connectedChips = screen.getAllByText('connected');
        expect(connectedChips.length).toBe(4);
    });

    it('shows agent policy values', () => {
        renderWithProviders(<SettingsPage />);
        expect(screen.getByText('85%')).toBeInTheDocument(); // auto-act threshold
        expect(screen.getByText('2')).toBeInTheDocument(); // max debate rounds
        expect(screen.getByText('30s')).toBeInTheDocument(); // agent timeout
    });
});

// ── Runbooks ──────────────────────────────────────────────────
describe('Runbooks Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<RunbooksPage />);
        expect(screen.getByText('Runbooks')).toBeInTheDocument();
    });

    it('renders search input', () => {
        renderWithProviders(<RunbooksPage />);
        expect(document.getElementById('runbook-search')).toBeInTheDocument();
    });

    it('renders runbook cards', () => {
        renderWithProviders(<RunbooksPage />);
        expect(screen.getByText('DB Pool Tuning Guide')).toBeInTheDocument();
        expect(screen.getByText('Rate Limiter Configuration')).toBeInTheDocument();
    });

    it('search filters runbooks', async () => {
        const user = userEvent.setup();
        renderWithProviders(<RunbooksPage />);

        const searchInput = document.getElementById('runbook-search');
        await user.type(searchInput, 'Redis');

        expect(screen.getByText('Redis Failover Recovery')).toBeInTheDocument();
        expect(screen.queryByText('DB Pool Tuning Guide')).not.toBeInTheDocument();
    });
});
