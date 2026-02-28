import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AppProvider } from '../hooks/useAppContext';

/**
 * Render a component wrapped in Router + AppProvider for testing.
 */
export function renderWithProviders(ui, options = {}) {
    function Wrapper({ children }) {
        return (
            <BrowserRouter>
                <AppProvider>
                    {children}
                </AppProvider>
            </BrowserRouter>
        );
    }
    return render(ui, { wrapper: Wrapper, ...options });
}
