import { useState } from 'react';
import { useApp } from '../hooks/useAppContext';
import { SIMULATION_SCENARIOS } from '../data/mockData';
import { X, Zap, Check, Loader } from 'lucide-react';

export default function SimulationModal() {
    const { simulationModalOpen, setSimulationModalOpen, runSimulation, simulationState } = useApp();
    const [selectedScenario, setSelectedScenario] = useState(SIMULATION_SCENARIOS[0].id);

    if (!simulationModalOpen && !simulationState) return null;

    // Show progress if simulation is running
    if (simulationState) {
        const steps = [
            'Event received',
            'Anomaly detected',
            'Severity classified',
            'Blast radius predicted',
            'Investigation started',
            'Hypothesis validated',
            'Fix recommended',
            'Actions executed',
            'Postmortem drafted',
        ];

        return (
            <div className="modal-overlay" id="simulation-progress">
                <div className="modal">
                    <div className="modal-header">
                        <h3 className="heading-md">Simulation Running</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                            <span className="body-sm">{simulationState.scenario.service}</span>
                        </div>
                    </div>
                    <div className="modal-body">
                        <div className="sim-progress">
                            {steps.map((step, i) => {
                                const isComplete = i < simulationState.step;
                                const isActive = i === simulationState.step;
                                return (
                                    <div key={step} className={`sim-step${isComplete ? ' complete' : ''}${isActive ? ' active' : ''}`}>
                                        <div className="sim-check">
                                            {isComplete && <Check size={12} />}
                                            {isActive && <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                                        </div>
                                        <span>{step}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
                <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    const scenario = SIMULATION_SCENARIOS.find(s => s.id === selectedScenario);

    return (
        <div className="modal-overlay" onClick={() => setSimulationModalOpen(false)} id="simulation-modal">
            <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3 className="heading-md">Simulate Event</h3>
                    <button className="drawer-close" onClick={() => setSimulationModalOpen(false)}>
                        <X size={16} />
                    </button>
                </div>
                <div className="modal-body">
                    <p className="body-sm" style={{ marginBottom: '16px' }}>
                        Trigger a deterministic demo scenario. New rows will appear in Events, Decisions, and Actions.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {SIMULATION_SCENARIOS.map(s => (
                            <label
                                key={s.id}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '12px',
                                    padding: '12px 16px',
                                    border: `1px solid ${selectedScenario === s.id ? 'var(--border-focus)' : 'var(--border-primary)'}`,
                                    borderRadius: 'var(--radius-lg)',
                                    cursor: 'pointer',
                                    background: selectedScenario === s.id ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                                    transition: 'all var(--transition-micro)',
                                }}
                            >
                                <input
                                    type="radio"
                                    name="scenario"
                                    value={s.id}
                                    checked={selectedScenario === s.id}
                                    onChange={() => setSelectedScenario(s.id)}
                                    style={{ marginTop: '2px', accentColor: 'var(--color-primary)' }}
                                />
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)', marginBottom: '2px' }}>{s.label}</div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{s.description}</div>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                                        <span className={`severity-chip ${s.severity === 'P1' ? 'critical' : 'warning'}`}>{s.severity}</span>
                                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{s.service}</span>
                                    </div>
                                </div>
                            </label>
                        ))}
                    </div>
                </div>
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={() => setSimulationModalOpen(false)}>
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={() => scenario && runSimulation(scenario)}
                        id="run-simulation-btn"
                    >
                        <Zap size={14} />
                        Run Simulation
                    </button>
                </div>
            </div>
        </div>
    );
}
