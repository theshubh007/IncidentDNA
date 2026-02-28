// ═══════════════════════════════════════════════════════════════
// Page Tests — Incidents
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/helpers';
import IncidentsPage from './IncidentsPage';

describe('Incidents Page', () => {
    it('renders the page heading', () => {
        renderWithProviders(<IncidentsPage />);
        expect(screen.getByText('Incidents')).toBeInTheDocument();
    });

    it('shows total and active count in subtitle', () => {
        renderWithProviders(<IncidentsPage />);
        expect(screen.getByText(/total/)).toBeInTheDocument();
        expect(screen.getByText(/active/)).toBeInTheDocument();
    });

    it('renders the incidents table', () => {
        renderWithProviders(<IncidentsPage />);
        expect(document.getElementById('incidents-table')).toBeInTheDocument();
    });

    it('renders table headers', () => {
        renderWithProviders(<IncidentsPage />);
        const table = document.getElementById('incidents-table');
        expect(within(table).getByText('ID')).toBeInTheDocument();
        expect(within(table).getByText('Severity')).toBeInTheDocument();
        expect(within(table).getByText('Service')).toBeInTheDocument();
        expect(within(table).getByText('Status')).toBeInTheDocument();
        expect(within(table).getByText('Confidence')).toBeInTheDocument();
    });

    it('renders incident rows with INC-XXX IDs', () => {
        renderWithProviders(<IncidentsPage />);
        expect(screen.getByText('INC-001')).toBeInTheDocument();
        expect(screen.getByText('INC-002')).toBeInTheDocument();
        expect(screen.getByText('INC-003')).toBeInTheDocument();
    });

    it('renders severity filter dropdown', () => {
        renderWithProviders(<IncidentsPage />);
        expect(document.getElementById('filter-severity')).toBeInTheDocument();
    });

    it('renders status filter dropdown', () => {
        renderWithProviders(<IncidentsPage />);
        expect(document.getElementById('filter-status')).toBeInTheDocument();
    });

    it('clicking a row opens the drawer', async () => {
        const user = userEvent.setup();
        renderWithProviders(<IncidentsPage />);

        const row = document.getElementById('incident-row-INC-001');
        await user.click(row);

        // Drawer should appear
        expect(document.getElementById('incident-drawer')).toBeInTheDocument();
    });

    it('drawer has 5 tabs', async () => {
        const user = userEvent.setup();
        renderWithProviders(<IncidentsPage />);

        await user.click(document.getElementById('incident-row-INC-001'));

        expect(document.getElementById('drawer-tab-timeline')).toBeInTheDocument();
        expect(document.getElementById('drawer-tab-blast-radius')).toBeInTheDocument();
        expect(document.getElementById('drawer-tab-patterns')).toBeInTheDocument();
        expect(document.getElementById('drawer-tab-actions')).toBeInTheDocument();
        expect(document.getElementById('drawer-tab-postmortem')).toBeInTheDocument();
    });

    it('filtering by severity works', async () => {
        const user = userEvent.setup();
        renderWithProviders(<IncidentsPage />);

        const filter = document.getElementById('filter-severity');
        await user.selectOptions(filter, 'info');

        // Only info-severity incidents should appear
        expect(screen.getByText('INC-004')).toBeInTheDocument();
        expect(screen.queryByText('INC-001')).not.toBeInTheDocument();
    });

    it('drawer close button works', async () => {
        const user = userEvent.setup();
        renderWithProviders(<IncidentsPage />);

        await user.click(document.getElementById('incident-row-INC-001'));
        expect(document.getElementById('incident-drawer')).toBeInTheDocument();

        // Click close button
        const closeBtn = document.querySelector('.drawer-close');
        await user.click(closeBtn);

        expect(document.getElementById('incident-drawer')).not.toBeInTheDocument();
    });
});
