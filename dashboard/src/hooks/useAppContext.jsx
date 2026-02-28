import { createContext, useContext, useState, useCallback, useRef } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [environment, setEnvironment] = useState('prod');
    const [toasts, setToasts] = useState([]);
    const [simulationState, setSimulationState] = useState(null); // null | { scenario, step, events }
    const [simulationModalOpen, setSimulationModalOpen] = useState(false);
    const [liveEvents, setLiveEvents] = useState([]);
    const [liveDecisions, setLiveDecisions] = useState([]);
    const [liveActions, setLiveActions] = useState([]);
    const toastIdRef = useRef(0);

    const addToast = useCallback((message, type = 'info') => {
        const id = ++toastIdRef.current;
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
            setTimeout(() => {
                setToasts(prev => prev.filter(t => t.id !== id));
            }, 200);
        }, 3500);
    }, []);

    const runSimulation = useCallback((scenario) => {
        setSimulationState({ scenario, step: 0, events: [] });
        setSimulationModalOpen(false);

        const steps = [
            { label: 'Event received', delay: 400 },
            { label: 'Anomaly detected', delay: 800 },
            { label: 'Severity classified', delay: 600 },
            { label: 'Blast radius predicted', delay: 700 },
            { label: 'Investigation started', delay: 1200 },
            { label: 'Hypothesis validated', delay: 900 },
            { label: 'Fix recommended', delay: 500 },
            { label: 'Actions executed', delay: 600 },
            { label: 'Postmortem drafted', delay: 400 },
        ];

        let currentStep = 0;
        const newEventId = `INC-${String(Math.floor(Math.random() * 900) + 100).padStart(3, '0')}`;

        const advance = () => {
            if (currentStep < steps.length) {
                setSimulationState(prev => prev ? { ...prev, step: currentStep + 1 } : null);

                if (currentStep === 0) {
                    setLiveEvents(prev => [{
                        id: newEventId,
                        service: scenario.service,
                        type: scenario.anomalyType,
                        severity: scenario.severity,
                        timestamp: new Date().toISOString(),
                    }, ...prev]);
                    addToast(`Event received from ${scenario.service}`, 'info');
                } else if (currentStep === 4) {
                    setLiveDecisions(prev => [{
                        id: `DEC-${Date.now()}`,
                        incidentId: newEventId,
                        agent: 'Ag2-Investigator',
                        reasoning: `Root cause: ${scenario.anomalyType.replace(/_/g, ' ')}`,
                        confidence: 0.89,
                        timestamp: new Date().toISOString(),
                    }, ...prev]);
                } else if (currentStep === 7) {
                    setLiveActions(prev => [
                        { id: `ACT-${Date.now()}`, incidentId: newEventId, type: 'SLACK_POST_MESSAGE', status: 'sent', timestamp: new Date().toISOString() },
                        { id: `ACT-${Date.now() + 1}`, incidentId: newEventId, type: 'GITHUB_CREATE_ISSUE', status: 'created', timestamp: new Date().toISOString() },
                        ...prev,
                    ]);
                    addToast('Slack message sent', 'success');
                    addToast('GitHub issue created', 'success');
                } else if (currentStep === 8) {
                    addToast('Auto postmortem drafted', 'success');
                }

                currentStep++;
                setTimeout(advance, steps[currentStep - 1].delay);
            } else {
                setTimeout(() => {
                    setSimulationState(null);
                    addToast('Simulation complete — pipeline finished', 'success');
                }, 500);
            }
        };

        setTimeout(advance, 300);
    }, [addToast]);

    const value = {
        sidebarCollapsed, setSidebarCollapsed,
        environment, setEnvironment,
        toasts, addToast,
        simulationState, simulationModalOpen, setSimulationModalOpen,
        runSimulation,
        liveEvents, liveDecisions, liveActions,
    };

    return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}
