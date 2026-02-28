// ═══════════════════════════════════════════════════════════════
// Integration Tests — Full App Routing & Cross-Component
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';

beforeEach(() => {
    cleanup();
    window.history.pushState({}, '', '/');
});

describe('Integration — App Routing', () => {
    it('renders the app without crashing', () => {
        render(<App />);
        expect(screen.getByText('Control Tower')).toBeInTheDocument();
    });

    it('navigates to Incidents page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-incidents'));

        await waitFor(() => {
            expect(screen.getByText(/total/)).toBeInTheDocument();
            expect(document.getElementById('incidents-table')).toBeInTheDocument();
        });
    });

    it('navigates to Releases page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-releases'));

        await waitFor(() => {
            expect(document.getElementById('releases-table')).toBeInTheDocument();
        });
    });

    it('navigates to Services page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-services'));

        await waitFor(() => {
            expect(document.getElementById('services-page')).toBeInTheDocument();
        });
    });

    it('navigates to Postmortems page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-postmortems'));

        await waitFor(() => {
            expect(document.getElementById('postmortems-page')).toBeInTheDocument();
        });
    });

    it('navigates to Audit page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-audit'));

        await waitFor(() => {
            expect(document.getElementById('audit-table')).toBeInTheDocument();
        });
    });

    it('navigates to Settings page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-settings'));

        await waitFor(() => {
            expect(document.getElementById('settings-page')).toBeInTheDocument();
        });
    });

    it('navigates to Runbooks page via sidebar', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('nav-runbooks'));

        await waitFor(() => {
            expect(document.getElementById('runbooks-page')).toBeInTheDocument();
        });
    });

    it('navigates back to Overview', async () => {
        const user = userEvent.setup();
        render(<App />);

        // Go to incidents first
        await user.click(document.getElementById('nav-incidents'));
        await waitFor(() => {
            expect(document.getElementById('incidents-table')).toBeInTheDocument();
        });

        // Go back to overview
        await user.click(document.getElementById('nav-overview'));
        await waitFor(() => {
            expect(screen.getByText('Control Tower')).toBeInTheDocument();
        });
    });
});

describe('Integration — Sidebar Collapse', () => {
    it('sidebar collapses and expands correctly', async () => {
        const user = userEvent.setup();
        render(<App />);

        // Initially expanded
        const collapseBtn = screen.getByLabelText('Collapse sidebar');
        expect(collapseBtn).toBeInTheDocument();

        // Collapse
        await user.click(collapseBtn);

        await waitFor(() => {
            expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
        });

        // Expand
        await user.click(screen.getByLabelText('Expand sidebar'));

        await waitFor(() => {
            expect(screen.getByLabelText('Collapse sidebar')).toBeInTheDocument();
        });
    });

    it('main content gets sidebar-collapsed class when collapsed', async () => {
        const user = userEvent.setup();
        render(<App />);

        const main = document.querySelector('.app-main');
        expect(main.classList.contains('sidebar-collapsed')).toBe(false);

        await user.click(screen.getByLabelText('Collapse sidebar'));

        await waitFor(() => {
            expect(main.classList.contains('sidebar-collapsed')).toBe(true);
        });
    });
});

describe('Integration — Environment Switch', () => {
    it('switches between Prod and Staging', async () => {
        const user = userEvent.setup();
        render(<App />);

        const prodBtn = document.getElementById('env-prod');
        const stagingBtn = document.getElementById('env-staging');

        // Prod is active by default
        expect(prodBtn.classList.contains('active')).toBe(true);
        expect(stagingBtn.classList.contains('active')).toBe(false);

        // Switch to staging
        await user.click(stagingBtn);
        expect(stagingBtn.classList.contains('active')).toBe(true);
        expect(prodBtn.classList.contains('active')).toBe(false);

        // Switch back to prod
        await user.click(prodBtn);
        expect(prodBtn.classList.contains('active')).toBe(true);
    });
});

describe('Integration — Simulation Flow', () => {
    it('Simulate Event button opens modal', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('simulate-event-btn'));

        await waitFor(() => {
            expect(document.getElementById('simulation-modal')).toBeInTheDocument();
        });
    });

    it('modal shows 3 scenario options', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('simulate-event-btn'));

        await waitFor(() => {
            expect(screen.getByText('Payment Error Spike')).toBeInTheDocument();
            expect(screen.getByText('Latency Regression')).toBeInTheDocument();
            expect(screen.getByText('DB Pool Exhaustion')).toBeInTheDocument();
        });
    });

    it('modal can be closed by Cancel', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('simulate-event-btn'));

        await waitFor(() => {
            expect(document.getElementById('simulation-modal')).toBeInTheDocument();
        });

        await user.click(screen.getByText('Cancel'));

        await waitFor(() => {
            expect(document.getElementById('simulation-modal')).not.toBeInTheDocument();
        });
    });

    it('running a simulation shows progress modal', async () => {
        const user = userEvent.setup();
        render(<App />);

        await user.click(document.getElementById('simulate-event-btn'));

        await waitFor(() => {
            expect(document.getElementById('simulation-modal')).toBeInTheDocument();
        });

        await user.click(document.getElementById('run-simulation-btn'));

        await waitFor(() => {
            expect(document.getElementById('simulation-progress')).toBeInTheDocument();
        });
    });
});

describe('Integration — Incident Drawer Flow', () => {
    it('full drawer interaction flow', async () => {
        const user = userEvent.setup();
        render(<App />);

        // Navigate to incidents
        await user.click(document.getElementById('nav-incidents'));
        await waitFor(() => {
            expect(document.getElementById('incidents-table')).toBeInTheDocument();
        });

        // Open drawer for INC-001
        await user.click(document.getElementById('incident-row-INC-001'));
        await waitFor(() => {
            expect(document.getElementById('incident-drawer')).toBeInTheDocument();
        });

        // Verify timeline tab is default
        expect(document.getElementById('drawer-tab-timeline').classList.contains('active')).toBe(true);

        // Switch to Pattern Memory tab
        await user.click(document.getElementById('drawer-tab-patterns'));
        expect(screen.getByText('92%')).toBeInTheDocument();

        // Switch to Actions tab
        await user.click(document.getElementById('drawer-tab-actions'));
        expect(screen.getByText(/slack/i)).toBeInTheDocument();

        // Switch to Postmortem tab
        await user.click(document.getElementById('drawer-tab-postmortem'));
        expect(screen.getByText('Customer Impact')).toBeInTheDocument();
    });
});

describe('Integration — Cross-Page Data Consistency', () => {
    it('incidents referenced in overview are accessible in incidents page', async () => {
        const user = userEvent.setup();
        render(<App />);

        // Overview shows INC-001 reference (text split across elements)
        expect(screen.getByText('INC-001 · payment-service')).toBeInTheDocument();

        // Navigate to incidents page
        await user.click(document.getElementById('nav-incidents'));

        await waitFor(() => {
            expect(screen.getByText('INC-001')).toBeInTheDocument();
        });
    });
});
