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

    it('renders the Simulate Event button', () => {
        renderWithProviders(<Toolbar />);
        expect(screen.getByText('Simulate Event')).toBeInTheDocument();
    });

    it('Simulate Event button has correct ID', () => {
        renderWithProviders(<Toolbar />);
        expect(document.getElementById('simulate-event-btn')).toBeInTheDocument();
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
