import { defineConfig } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

const database = path.join(mkdtempSync(path.join(tmpdir(), 'hireflow-e2e-')), 'accounts.sqlite3')

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: { baseURL: 'http://127.0.0.1:8000', channel: 'chrome', headless: true, reducedMotion: 'reduce' },
  webServer: {
    command: `${process.env.HIREFLOW_PYTHON || 'python'} -m uvicorn web_api:app --host 127.0.0.1 --port 8000`,
    cwd: path.resolve(import.meta.dirname, '..'),
    env: { HIREFLOW_DB_PATH: database, HIREFLOW_SIMILARITY_BACKEND: 'keyword' },
    url: 'http://127.0.0.1:8000/api/openapi.json',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
