import { test, expect } from '@playwright/test';

// Use pre-authenticated state
test.use({ storageState: 'tests/e2e/auth.json' });

test.describe('UI Security Enforcement', () => {

    test('Client-Side Injection: Unauthorized layer in localStorage is sanitized or rejected', async ({ page }) => {
        // Logging
        page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('response', response => {
            if (response.status() >= 400) console.log(`RES ERROR: ${response.status()} ${response.url()}`);
        });

        // 1. Mock Auth & System state
        await page.route('**/setup-complete', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    results: { MultiUserMode: true, RequiresAuth: true, LLMProvider: 'openai', VectorDB: 'lancedb' }
                })
            });
        });

        await page.route('**/api/system/logo*', async route => {
            const buffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==', 'base64');
            await route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, contentType: 'image/png', body: buffer });
        });

        // Mock Session Validations
        await page.route('**/api/system/check-token', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' } }));
        await page.route('**/validate-token', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ valid: true }) }));
        await page.route('**/api/system/refresh-user', async route => route.fulfill({
            status: 200,
            headers: { 'Access-Control-Allow-Origin': '*' },
            body: JSON.stringify({ username: 'user', role: 'default', id: 2, multi_user_mode: true })
        }));

        // 2. Mock /auth/layers
        await page.route('**/api/system/auth-layers', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    layers: [
                        { id: 'layer_system_public', name: 'System Public', type: 'SYSTEM', access: 'READ', color: 'blue' }
                    ]
                })
            });
        });

        // 3. Inject RESTRICTED layer into localStorage
        await page.goto('http://localhost:3001/');
        await page.evaluate(() => {
            const maliciousState = {
                state: {
                    activeLayerIds: ['layer_admin_secret'],
                    availableLayers: [],
                    isLoading: false
                },
                version: 0
            };
            window.localStorage.setItem('pandora-layer-storage', JSON.stringify(maliciousState));
        });

        // Mock workspace for chat
        await page.route('**/api/workspace/system-public', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    workspace: { id: 1, name: 'System Public', slug: 'system-public', vectorTag: 'public' }
                })
            });
        });

        // Mock chat stream
        let capturedLayerHeader = '';
        await page.route('**/api/v1/stream/chat', async route => {
            capturedLayerHeader = route.request().headers()['x-pandora-layer-id'] || '';
            await route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: '' });
        });

        // Mock helpers
        await page.route('**/api/workspace/*/chats', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ history: [] }) }));
        await page.route('**/api/workspace/*/suggested-messages', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ suggestedMessages: [] }) }));
        await page.route('**/api/workspace/*/pfp', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ pfpUrl: null }) }));

        // Navigate to chat
        await page.goto('http://localhost:3001/workspace/system-public');

        // Verify UI
        await expect(page.getByText('System Public')).toBeVisible();
        await expect(page.getByText('Admin Secret')).not.toBeVisible();

        // 5. Trigger a chat to see what header is sent
        const input = page.locator('#primary-prompt-input');
        await input.waitFor({ state: 'visible', timeout: 30000 });
        await input.fill('Hello security check');
        await page.keyboard.press('Enter');

        // 6. Assertions
        console.log('Captured Header:', capturedLayerHeader);
        expect(capturedLayerHeader).not.toContain('layer_admin_secret');
    });

    test('Mid-Session Revocation: UI handles 403 Forbidden', async ({ page }) => {
        page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));

        // 1. Mock Auth
        await page.route('**/setup-complete', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    results: { MultiUserMode: true, RequiresAuth: true, LLMProvider: 'openai', VectorDB: 'lancedb' }
                })
            });
        });

        await page.route('**/api/system/logo*', async route => {
            const buffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==', 'base64');
            await route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, contentType: 'image/png', body: buffer });
        });

        await page.route('**/api/system/check-token', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' } }));
        await page.route('**/validate-token', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ valid: true }) }));
        await page.route('**/api/system/refresh-user', async route => route.fulfill({
            status: 200,
            headers: { 'Access-Control-Allow-Origin': '*' },
            body: JSON.stringify({ username: 'engineer', role: 'engineering', id: 3, multi_user_mode: true })
        }));

        // 2. Mock /auth/layers
        await page.route('**/api/system/auth-layers', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    layers: [
                        { id: 'layer_engineering', name: 'Engineering', type: 'TEAM', access: 'READ', color: 'purple' }
                    ]
                })
            });
        });

        // 3. Inject Engineering Layer
        await page.goto('http://localhost:3001/');
        await page.evaluate(() => {
            window.localStorage.setItem('pandora-layer-storage', JSON.stringify({
                state: { activeLayerIds: ['layer_engineering'], availableLayers: [], isLoading: false },
                version: 0
            }));
        });

        // Mock workspace
        await page.route('**/api/workspace/engineering', async route => {
            await route.fulfill({
                status: 200,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({
                    workspace: {
                        id: 1,
                        name: 'Engineering',
                        slug: 'engineering',
                        vectorTag: 'engineering',
                        createdAt: '2023-01-01',
                        openAiTemp: 0.7,
                        lastModified: '2023-01-01'
                    }
                })
            });
        });

        // 4. Chat returns 403
        await page.route('**/api/v1/stream/chat', async route => {
            await route.fulfill({
                status: 403,
                headers: { 'Access-Control-Allow-Origin': '*' },
                contentType: 'application/json',
                body: JSON.stringify({ error: 'Access to layer_engineering revoked' })
            });
        });

        // Mock helpers
        await page.route('**/api/workspace/*/chats', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ history: [] }) }));
        await page.route('**/api/workspace/*/suggested-messages', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ suggestedMessages: [] }) }));
        await page.route('**/api/workspace/*/pfp', async route => route.fulfill({ status: 200, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ pfpUrl: null }) }));

        await page.goto('http://localhost:3001/workspace/engineering');

        const input = page.locator('#primary-prompt-input');
        await input.waitFor({ state: 'visible', timeout: 30000 });
        await input.fill('Is the system secure?');
        await page.keyboard.press('Enter');

        // 5. Expect UI Error Alert
        await expect(page.getByText('Access to layer_engineering revoked')).toBeVisible({ timeout: 10000 });
    });
});
