// ═══════════════════════════════════════════════════════════════
// config.js — Runtime configuration from environment variables
// All env vars are read here once; components import from this file
// ═══════════════════════════════════════════════════════════════

const config = {
    // API endpoints
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',

    // CrewAI
    crewaiEndpoint: import.meta.env.VITE_CREWAI_ENDPOINT || 'http://localhost:8001/run',
    crewaiApiKey: import.meta.env.VITE_CREWAI_API_KEY || '',

    // Composio
    composioApiKey: import.meta.env.VITE_COMPOSIO_API_KEY || '',
    composioSlackId: import.meta.env.VITE_COMPOSIO_SLACK_CONNECTION_ID || '',
    composioGithubId: import.meta.env.VITE_COMPOSIO_GITHUB_CONNECTION_ID || '',

    // Snowflake
    snowflakeWarehouse: import.meta.env.VITE_SNOWFLAKE_WAREHOUSE || 'COMPUTE_WH',
    snowflakeDatabase: import.meta.env.VITE_SNOWFLAKE_DATABASE || 'INCIDENTDNA',

    // Feature flags
    useLiveData: import.meta.env.VITE_USE_LIVE_DATA === 'true',
    enableRealtime: import.meta.env.VITE_ENABLE_REALTIME === 'true',
    enableSimulation: import.meta.env.VITE_ENABLE_SIMULATION !== 'false',

    // App
    appName: import.meta.env.VITE_APP_NAME || 'ReleaseShield',
    appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0-beta',
    defaultEnv: import.meta.env.VITE_DEFAULT_ENVIRONMENT || 'prod',
};

export default config;
