/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Public API root for the backend, e.g. "https://<backend>.up.railway.app/api/v1".
   * Leave unset in local dev to use the Vite proxy's relative "/api/v1".
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
