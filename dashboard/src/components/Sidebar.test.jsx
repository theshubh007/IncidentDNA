// ═══════════════════════════════════════════════════════════════
// Component Tests — Sidebar
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/helpers';
import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
    it('renders all navigation items', () => {
        renderWithProviders(<Sidebar />);

        expect(screen.getByText('Overview')).toBeInTheDocument();
        expect(screen.getByText('Incidents')).toBeInTheDocument();
        expect(screen.getByText('Releases')).toBeInTheDocument();
        expect(screen.getByText('Services')).toBeInTheDocument();
        expect(screen.getByText('Runbooks')).toBeInTheDocument();
        expect(screen.getByText('Postmortems')).toBeInTheDocument();
        expect(screen.getByText('Audit Log')).toBeInTheDocument();
        expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('renders the brand name', () => {
        renderWithProviders(<Sidebar />);
        expect(screen.getByText('FortressAI')).toBeInTheDocument();
    });

    it('renders the pipeline health status', () => {
        renderWithProviders(<Sidebar />);
        expect(screen.getByText('Pipeline Healthy')).toBeInTheDocument();
    });

    it('has unique IDs for each nav item', () => {
        renderWithProviders(<Sidebar />);
        const navIds = ['nav-overview', 'nav-incidents', 'nav-releases', 'nav-services', 'nav-runbooks', 'nav-postmortems', 'nav-audit', 'nav-repository', 'nav-settings'];
        navIds.forEach(id => {
            expect(document.getElementById(id)).toBeInTheDocument();
        });
    });

    it('has a collapse button with correct aria-label', () => {
        renderWithProviders(<Sidebar />);
        const btn = screen.getByLabelText('Collapse sidebar');
        expect(btn).toBeInTheDocument();
    });

    it('collapse button toggles sidebar state', async () => {
        const user = userEvent.setup();
        renderWithProviders(<Sidebar />);

        const btn = screen.getByLabelText('Collapse sidebar');
        await user.click(btn);

        // After collapse, the aria-label should change
        expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
    });

    it('Overview link is active on root path', () => {
        renderWithProviders(<Sidebar />);
        const overviewBtn = document.getElementById('nav-overview');
        expect(overviewBtn.classList.contains('active')).toBe(true);
    });
});
