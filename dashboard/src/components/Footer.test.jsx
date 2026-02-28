// ═══════════════════════════════════════════════════════════════
// Component Tests — Footer
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/helpers';
import Footer from './Footer';

describe('Footer Component', () => {
    it('renders warehouse indicator', () => {
        renderWithProviders(<Footer />);
        expect(screen.getByText(/COMPUTE_WH/)).toBeInTheDocument();
        expect(screen.getByText(/INCIDENTDNA/)).toBeInTheDocument();
    });

    it('renders last refresh time', () => {
        renderWithProviders(<Footer />);
        expect(screen.getByText(/Last refresh:/)).toBeInTheDocument();
    });

    it('renders build version hash', () => {
        renderWithProviders(<Footer />);
        expect(screen.getByText(/v1\.0\.0-beta/)).toBeInTheDocument();
        expect(screen.getByText(/sha-a1b2c3d/)).toBeInTheDocument();
    });
});
