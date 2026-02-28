// ═══════════════════════════════════════════════════════════════
// Component Tests — Toolbar
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/helpers';
import Toolbar from './Toolbar';

describe('Toolbar Component', () => {
    it('renders the search bar', () => {
        renderWithProviders(<Toolbar />);
        expect(screen.getByText('Search incidents, services…')).toBeInTheDocument();
    });

    it('renders the environment switch', () => {
        renderWithProviders(<Toolbar />);
        expect(screen.getByText('Prod')).toBeInTheDocument();
        expect(screen.getByText('Staging')).toBeInTheDocument();
    });

    it('renders the Simulate Event button', () => {
        renderWithProviders(<Toolbar />);
        expect(screen.getByText('Simulate Event')).toBeInTheDocument();
    });

    it('Simulate Event button has correct ID', () => {
        renderWithProviders(<Toolbar />);
        expect(document.getElementById('simulate-event-btn')).toBeInTheDocument();
    });

    it('Prod is active by default', () => {
        renderWithProviders(<Toolbar />);
        const prodBtn = document.getElementById('env-prod');
        expect(prodBtn.classList.contains('active')).toBe(true);
    });

    it('clicking Staging switches environment', async () => {
        const user = userEvent.setup();
        renderWithProviders(<Toolbar />);

        const stagingBtn = document.getElementById('env-staging');
        await user.click(stagingBtn);
        expect(stagingBtn.classList.contains('active')).toBe(true);
    });

    it('notifications button has a badge', () => {
        renderWithProviders(<Toolbar />);
        const notifBtn = document.getElementById('notifications-btn');
        expect(notifBtn).toBeInTheDocument();
        const badge = notifBtn.querySelector('.badge');
        expect(badge).toBeInTheDocument();
    });

    it('renders user menu', () => {
        renderWithProviders(<Toolbar />);
        expect(document.getElementById('user-menu')).toBeInTheDocument();
    });
});
