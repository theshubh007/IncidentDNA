// ═══════════════════════════════════════════════════════════════
// Page Tests — Overview (Control Tower)
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/helpers';
import OverviewPage from './OverviewPage';

describe('Overview Page', () => {
    it('renders the Control Tower heading', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Control Tower')).toBeInTheDocument();
    });

    it('renders the subtitle', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Real-time autonomous release safety overview')).toBeInTheDocument();
    });

    it('renders all 4 metric cards', () => {
        renderWithProviders(<OverviewPage />);
        // Note: CSS text-transform:uppercase makes labels visually uppercase,
        // but DOM text is mixed case
        expect(screen.getByText('Active Incidents')).toBeInTheDocument();
        expect(screen.getByText('Deploy Confidence')).toBeInTheDocument();
        expect(screen.getByText('Error Rate')).toBeInTheDocument();
        expect(screen.getByText('Avg MTTR')).toBeInTheDocument();
    });

    it('renders metric values', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('1')).toBeInTheDocument(); // active incidents
        expect(screen.getByText('72%')).toBeInTheDocument(); // deploy confidence
        expect(screen.getByText('4.0%')).toBeInTheDocument(); // error rate
        expect(screen.getByText('11.2m')).toBeInTheDocument(); // avg mttr
    });

    it('renders the Live Agent Loop', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Live Agent Loop')).toBeInTheDocument();
    });

    it('renders all 7 stepper steps', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Detect')).toBeInTheDocument();
        expect(screen.getByText('Classify')).toBeInTheDocument();
        // 'Blast Radius' appears both in stepper and panel card title
        expect(screen.getAllByText('Blast Radius').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('Investigate')).toBeInTheDocument();
        expect(screen.getByText('Validate')).toBeInTheDocument();
        expect(screen.getByText('Action')).toBeInTheDocument();
        // 'Postmortem' may also appear in panel
        expect(screen.getAllByText('Postmortem').length).toBeGreaterThanOrEqual(1);
    });

    it('renders the Blast Radius panel', () => {
        renderWithProviders(<OverviewPage />);
        expect(document.getElementById('blast-radius-panel')).toBeInTheDocument();
    });

    it('renders Similar Past Incidents', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Similar Past Incidents')).toBeInTheDocument();
        expect(screen.getByText('INC-012')).toBeInTheDocument();
        expect(screen.getByText('92%')).toBeInTheDocument();
    });

    it('renders Quick Simulate section', () => {
        renderWithProviders(<OverviewPage />);
        expect(screen.getByText('Quick Simulate')).toBeInTheDocument();
    });

    it('has correct element IDs for testing', () => {
        renderWithProviders(<OverviewPage />);
        expect(document.getElementById('overview-page')).toBeInTheDocument();
        expect(document.getElementById('live-agent-loop')).toBeInTheDocument();
        expect(document.getElementById('blast-radius-panel')).toBeInTheDocument();
        expect(document.getElementById('pattern-memory-panel')).toBeInTheDocument();
        expect(document.getElementById('quick-simulate')).toBeInTheDocument();
    });

    it('stepper steps are expandable', async () => {
        const user = userEvent.setup();
        renderWithProviders(<OverviewPage />);

        // Click on the "Detect" step label to expand
        const detectLabels = screen.getAllByText('Detect');
        await user.click(detectLabels[0]);

        // Evidence should now be visible
        expect(screen.getByText('ANALYTICS.METRIC_DEVIATIONS')).toBeInTheDocument();
    });
});
