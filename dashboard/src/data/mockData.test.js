// ═══════════════════════════════════════════════════════════════
// Unit Tests — Mock Data Layer
// Verifies data integrity, shape, and helper functions
// ═══════════════════════════════════════════════════════════════
import { describe, it, expect } from 'vitest';
import {
    SERVICES, INCIDENTS_DATA, RELEASES_DATA, AUDIT_LOG_DATA,
    METRICS_OVERVIEW, STEPPER_STATES, DEPENDENCY_GRAPH,
    SIMULATION_SCENARIOS, POSTMORTEMS_DATA, generateSparkline,
    SERVICE_SPARKLINES,
} from '../data/mockData';

describe('Mock Data — Services', () => {
    it('should have at least 5 services', () => {
        expect(SERVICES.length).toBeGreaterThanOrEqual(5);
    });

    it('every service has required fields', () => {
        SERVICES.forEach(s => {
            expect(s).toHaveProperty('id');
            expect(s).toHaveProperty('name');
            expect(s).toHaveProperty('status');
            expect(s).toHaveProperty('uptime');
            expect(s).toHaveProperty('latency');
            expect(s).toHaveProperty('errorRate');
            expect(s).toHaveProperty('dependencies');
            expect(Array.isArray(s.dependencies)).toBe(true);
        });
    });

    it('service IDs are unique', () => {
        const ids = SERVICES.map(s => s.id);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('uptime is between 0 and 100', () => {
        SERVICES.forEach(s => {
            expect(s.uptime).toBeGreaterThanOrEqual(0);
            expect(s.uptime).toBeLessThanOrEqual(100);
        });
    });
});

describe('Mock Data — Incidents', () => {
    it('should have at least 3 incidents', () => {
        expect(INCIDENTS_DATA.length).toBeGreaterThanOrEqual(3);
    });

    it('every incident has required fields', () => {
        INCIDENTS_DATA.forEach(inc => {
            expect(inc).toHaveProperty('id');
            expect(inc).toHaveProperty('severity');
            expect(inc).toHaveProperty('service');
            expect(inc).toHaveProperty('detected');
            expect(inc).toHaveProperty('status');
            expect(inc).toHaveProperty('confidence');
            expect(inc).toHaveProperty('blastRadius');
            expect(inc).toHaveProperty('actionsFired');
            expect(inc).toHaveProperty('rootCause');
            expect(inc).toHaveProperty('timeline');
            expect(inc).toHaveProperty('blastRadiusDetail');
            expect(inc).toHaveProperty('patternMemory');
            expect(inc).toHaveProperty('actions');
        });
    });

    it('incident IDs follow INC-XXX format', () => {
        INCIDENTS_DATA.forEach(inc => {
            expect(inc.id).toMatch(/^INC-\d{3}$/);
        });
    });

    it('severity is one of valid values', () => {
        const validSeverities = ['critical', 'warning', 'info'];
        INCIDENTS_DATA.forEach(inc => {
            expect(validSeverities).toContain(inc.severity);
        });
    });

    it('confidence is between 0 and 1', () => {
        INCIDENTS_DATA.forEach(inc => {
            expect(inc.confidence).toBeGreaterThanOrEqual(0);
            expect(inc.confidence).toBeLessThanOrEqual(1);
        });
    });

    it('timeline entries have required fields', () => {
        INCIDENTS_DATA.forEach(inc => {
            inc.timeline.forEach(step => {
                expect(step).toHaveProperty('time');
                expect(step).toHaveProperty('agent');
                expect(step).toHaveProperty('action');
                expect(step).toHaveProperty('status');
            });
        });
    });

    it('at least one incident has a postmortem', () => {
        const withPostmortem = INCIDENTS_DATA.filter(i => i.postmortem !== null);
        expect(withPostmortem.length).toBeGreaterThanOrEqual(1);
    });

    it('postmortem has required fields', () => {
        INCIDENTS_DATA.filter(i => i.postmortem).forEach(inc => {
            expect(inc.postmortem).toHaveProperty('summary');
            expect(inc.postmortem).toHaveProperty('customerImpact');
            expect(inc.postmortem).toHaveProperty('rootCause');
            expect(inc.postmortem).toHaveProperty('actionItems');
            expect(Array.isArray(inc.postmortem.actionItems)).toBe(true);
        });
    });

    it('pattern memory entries have similarity scores between 0 and 1', () => {
        INCIDENTS_DATA.forEach(inc => {
            inc.patternMemory.forEach(pm => {
                expect(pm.similarity).toBeGreaterThanOrEqual(0);
                expect(pm.similarity).toBeLessThanOrEqual(1);
            });
        });
    });
});

describe('Mock Data — Releases', () => {
    it('should have at least 3 releases', () => {
        expect(RELEASES_DATA.length).toBeGreaterThanOrEqual(3);
    });

    it('every release has required fields', () => {
        RELEASES_DATA.forEach(r => {
            expect(r).toHaveProperty('id');
            expect(r).toHaveProperty('service');
            expect(r).toHaveProperty('version');
            expect(r).toHaveProperty('confidence');
            expect(r).toHaveProperty('risk');
            expect(r).toHaveProperty('riskFactors');
            expect(r).toHaveProperty('guardrails');
        });
    });

    it('confidence is between 0 and 100', () => {
        RELEASES_DATA.forEach(r => {
            expect(r.confidence).toBeGreaterThanOrEqual(0);
            expect(r.confidence).toBeLessThanOrEqual(100);
        });
    });

    it('risk is one of valid values', () => {
        const validRisks = ['low', 'medium', 'high'];
        RELEASES_DATA.forEach(r => {
            expect(validRisks).toContain(r.risk);
        });
    });
});

describe('Mock Data — Audit Log', () => {
    it('should have at least 5 audit entries', () => {
        expect(AUDIT_LOG_DATA.length).toBeGreaterThanOrEqual(5);
    });

    it('every entry has required fields', () => {
        AUDIT_LOG_DATA.forEach(entry => {
            expect(entry).toHaveProperty('actionId');
            expect(entry).toHaveProperty('decisionId');
            expect(entry).toHaveProperty('toolkit');
            expect(entry).toHaveProperty('actionType');
            expect(entry).toHaveProperty('status');
            expect(entry).toHaveProperty('retryCount');
            expect(entry).toHaveProperty('idempotencyKey');
            expect(entry).toHaveProperty('timestamp');
            expect(entry).toHaveProperty('request');
            expect(entry).toHaveProperty('response');
        });
    });

    it('action IDs are unique', () => {
        const ids = AUDIT_LOG_DATA.map(e => e.actionId);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('retryCount is a non-negative integer', () => {
        AUDIT_LOG_DATA.forEach(entry => {
            expect(entry.retryCount).toBeGreaterThanOrEqual(0);
            expect(Number.isInteger(entry.retryCount)).toBe(true);
        });
    });

    it('includes at least one skipped_duplicate entry', () => {
        const dupes = AUDIT_LOG_DATA.filter(e => e.status === 'skipped_duplicate');
        expect(dupes.length).toBeGreaterThanOrEqual(1);
    });
});

describe('Mock Data — Metrics Overview', () => {
    it('has all required metric fields', () => {
        expect(METRICS_OVERVIEW).toHaveProperty('activeIncidents');
        expect(METRICS_OVERVIEW).toHaveProperty('deployConfidence');
        expect(METRICS_OVERVIEW).toHaveProperty('errorRate');
        expect(METRICS_OVERVIEW).toHaveProperty('latencyP99');
        expect(METRICS_OVERVIEW).toHaveProperty('mttrAvg');
        expect(METRICS_OVERVIEW).toHaveProperty('mttrIndustry');
    });

    it('MTTR average is less than industry baseline', () => {
        expect(METRICS_OVERVIEW.mttrAvg).toBeLessThan(METRICS_OVERVIEW.mttrIndustry);
    });
});

describe('Mock Data — Stepper States', () => {
    it('has 7 stepper steps (full pipeline)', () => {
        expect(STEPPER_STATES.length).toBe(7);
    });

    it('steps follow the correct order', () => {
        const expectedOrder = ['detect', 'classify', 'blast-radius', 'investigate', 'validate', 'action', 'postmortem'];
        const actualOrder = STEPPER_STATES.map(s => s.id);
        expect(actualOrder).toEqual(expectedOrder);
    });

    it('each step has required fields', () => {
        STEPPER_STATES.forEach(step => {
            expect(step).toHaveProperty('id');
            expect(step).toHaveProperty('label');
            expect(step).toHaveProperty('status');
            expect(step).toHaveProperty('timestamp');
            expect(step).toHaveProperty('detail');
            expect(step).toHaveProperty('evidence');
        });
    });
});

describe('Mock Data — Simulation Scenarios', () => {
    it('has exactly 3 scenarios', () => {
        expect(SIMULATION_SCENARIOS.length).toBe(3);
    });

    it('scenarios cover the required types', () => {
        const labels = SIMULATION_SCENARIOS.map(s => s.label);
        expect(labels).toContain('LLM Gateway Error Spike');
        expect(labels).toContain('Latency Regression');
        expect(labels).toContain('DB Pool Exhaustion');
    });

    it('each scenario has required fields', () => {
        SIMULATION_SCENARIOS.forEach(s => {
            expect(s).toHaveProperty('id');
            expect(s).toHaveProperty('label');
            expect(s).toHaveProperty('description');
            expect(s).toHaveProperty('service');
            expect(s).toHaveProperty('anomalyType');
            expect(s).toHaveProperty('severity');
        });
    });
});

describe('Mock Data — Dependency Graph', () => {
    it('has nodes and edges', () => {
        expect(DEPENDENCY_GRAPH.nodes.length).toBeGreaterThan(0);
        expect(DEPENDENCY_GRAPH.edges.length).toBeGreaterThan(0);
    });

    it('all edge references exist as nodes', () => {
        const nodeIds = new Set(DEPENDENCY_GRAPH.nodes.map(n => n.id));
        DEPENDENCY_GRAPH.edges.forEach(edge => {
            expect(nodeIds.has(edge.from)).toBe(true);
            expect(nodeIds.has(edge.to)).toBe(true);
        });
    });
});

describe('Mock Data — Postmortems', () => {
    it('postmortems are derived from incidents with postmortems', () => {
        const incidentsWithPM = INCIDENTS_DATA.filter(i => i.postmortem !== null);
        expect(POSTMORTEMS_DATA.length).toBe(incidentsWithPM.length);
    });

    it('each postmortem references a valid incident', () => {
        const incidentIds = INCIDENTS_DATA.map(i => i.id);
        POSTMORTEMS_DATA.forEach(pm => {
            expect(incidentIds).toContain(pm.incidentId);
        });
    });
});

describe('Helper — generateSparkline', () => {
    it('generates correct length array', () => {
        const data = generateSparkline(30, 50, 10);
        expect(data.length).toBe(30);
    });

    it('default length is 24', () => {
        const data = generateSparkline();
        expect(data.length).toBe(24);
    });

    it('values are non-negative', () => {
        const data = generateSparkline(100, 5, 3);
        data.forEach(v => expect(v).toBeGreaterThanOrEqual(0));
    });

    it('spike is applied at correct index', () => {
        const data = generateSparkline(10, 50, 5, { index: 5, value: 500 });
        expect(data[5]).toBe(500);
    });
});

describe('Mock Data — Service Sparklines', () => {
    it('has sparkline data for all services', () => {
        SERVICES.forEach(s => {
            expect(SERVICE_SPARKLINES).toHaveProperty(s.id);
            expect(SERVICE_SPARKLINES[s.id]).toHaveProperty('latency');
            expect(SERVICE_SPARKLINES[s.id]).toHaveProperty('errorRate');
        });
    });
});
