import { test, expect } from '@playwright/test';

test.describe.skip('Engine Room Validation', () => {

    test('Loads WorkerHUD and Shows Data', async ({ page }) => {
        // Log all network activity
        page.on('request', request => console.log('>>', request.method(), request.url()));
        page.on('response', response => console.log('<<', response.status(), response.url()));
        page.on('console', msg => console.log('BROWSER LOG:', msg.text()));

        // Mock Auth check to Bypass Login completely (Single User Mode)
        await page.route('**/setup-complete', async route => {
            console.log('MOCK HIT: setup-complete');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    results: {
                        MultiUserMode: false,
                        multi_user_mode: false,
                        RequiresAuth: false,
                        requires_auth: false,
                        LLMProvider: 'openai',
                        VectorDB: 'lancedb'
                    }
                })
            });
        });

        // Mock System endpoints to prevent background 401s from wiping session
        await page.route('**/api/system/check-token', async route => route.fulfill({ status: 200 }));
        await page.route('**/api/system/refresh-user', async route => route.fulfill({
            status: 200,
            body: JSON.stringify({ username: 'admin', role: 'admin', id: 1, multi_user_mode: false })
        }));
        await page.route('**/api/system/pfp/*', async route => route.fulfill({ status: 200, body: '' }));
        await page.route('**/api/system/logo*', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ url: '' }) }));
        await page.route('**/api/workspaces', async route => route.fulfill({ status: 200, body: JSON.stringify([]) }));
        await page.route('**/api/system/footer-data', async route => route.fulfill({ status: 200, body: JSON.stringify({}) }));
        await page.route('**/api/system/support-email', async route => route.fulfill({ status: 200, body: JSON.stringify({ email: 'test@test.com' }) }));
        await page.route('**/validate-token', async route => route.fulfill({ status: 200, body: JSON.stringify({ valid: true }) }));

        // Initialize LocalStorage for Admin User (Single User Admin)
        await page.addInitScript(() => {
            window.localStorage.setItem('anythingllm_user', JSON.stringify({
                username: 'admin',
                role: 'admin',
                id: 1,
            }));
            window.localStorage.setItem('anythingllm_authToken', 'fake-token');
        });

        // Mock the Engine Room Data
        await page.route('**/api/v1/ops/health/overview', async route => {
            console.log('MOCK HIT: health/overview');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    vector_stats: { total_chunks: 100 },
                    graph_connected: true,
                    queue_stats: { heavy_lifting: 2, audio_processing: 3, fast_lane: 0 },
                    api_latency_ms: 150,
                    timestamp: new Date().toISOString(),
                    active_table: 'vectors'
                })
            });
        });

        await page.route('**/api/v1/ops/jobs/active', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ jobs: [], total: 0 })
            });
        });

        await page.route('**/api/v1/admin/layers*', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([])
            });
        });

        // Navigate to Engine Room
        await page.goto('http://localhost:3001/engine-room');
        await page.waitForLoadState('networkidle');

        console.log('Current URL after nav:', page.url());

        if (!page.url().includes('engine-room')) {
            console.log('Redirected away from engine-room. Auth mock likely failed.');
            const body = await page.textContent('body');
            // console.log('Page body:', body); 
        }

        // Check if GPU Nodes shows 5 (2 + 3)
        await expect(page.getByText('5', { exact: true })).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('/ 8 pods')).toBeVisible();

        // Check Latency
        await expect(page.getByText('150')).toBeVisible();

        // Check Active Table
        await expect(page.getByText('vectors', { exact: true })).toBeVisible();
    });

    test('Switch Table Trigger', async ({ page }) => {
        // Mock Auth check to Bypass Login completely (Single User Mode)
        await page.route('**/setup-complete', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    results: {
                        MultiUserMode: false,
                        multi_user_mode: false,
                        RequiresAuth: false,
                        requires_auth: false,
                        LLMProvider: 'openai',
                        VectorDB: 'lancedb'
                    }
                })
            });
        });

        // Mock System endpoints preventing 401s
        await page.route('**/api/system/check-token', async route => route.fulfill({ status: 200 }));
        await page.route('**/api/system/refresh-user', async route => route.fulfill({ status: 200, body: JSON.stringify({ username: 'admin', role: 'admin', id: 1, multi_user_mode: false }) }));
        await page.route('**/api/system/pfp/*', async route => route.fulfill({ status: 200 }));
        await page.route('**/api/system/logo*', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ url: '' }) }));
        await page.route('**/api/workspaces', async route => route.fulfill({ status: 200, body: JSON.stringify([]) }));
        await page.route('**/api/system/footer-data', async route => route.fulfill({ status: 200, body: JSON.stringify({}) }));
        await page.route('**/api/system/support-email', async route => route.fulfill({ status: 200, body: JSON.stringify({ email: '' }) }));
        await page.route('**/validate-token', async route => route.fulfill({ status: 200, body: JSON.stringify({ valid: true }) }));

        // Initialize LocalStorage for Admin User
        await page.addInitScript(() => {
            window.localStorage.setItem('anythingllm_user', JSON.stringify({
                username: 'admin',
                role: 'admin',
                id: 1,
            }));
            window.localStorage.setItem('anythingllm_authToken', 'fake-token');
        });

        // Mock initial health
        await page.route('**/api/v1/ops/health/overview', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    vector_stats: {},
                    graph_connected: true,
                    queue_stats: {},
                    api_latency_ms: 50,
                    timestamp: new Date().toISOString(),
                    active_table: 'vectors'
                })
            });
        });

        // Mock switch table endpoint
        await page.route('**/api/v1/ops/switch-table', async route => {
            const request = route.request();
            const postData = JSON.parse(request.postData() || '{}');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    status: 'switched',
                    active_table: postData.table_name,
                    message: `Switched active table to ${postData.table_name}`
                })
            });
        });

        // Mock other endpoints to avoid errors
        await page.route('**/api/v1/ops/jobs/active', async route => route.fulfill({ body: JSON.stringify({ jobs: [] }) }));
        await page.route('**/api/v1/admin/layers*', async route => route.fulfill({ body: JSON.stringify([]) }));

        await page.goto('http://localhost:3001/engine-room');
        page.on('dialog', dialog => dialog.accept());

        await expect(page.getByText('vectors', { exact: true })).toBeVisible({ timeout: 10000 });

        await page.locator('button[title="Switch Active Table (Blue/Green)"]').click();
        await expect(page.getByText('vectors_v2', { exact: true })).toBeVisible({ timeout: 5000 });
    });
});
