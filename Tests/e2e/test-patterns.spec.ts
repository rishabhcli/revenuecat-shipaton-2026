import { expect, test } from '@playwright/test';

test.describe('original test-pattern development surface', () => {
  test('readiness is semantic and explicitly non-production', async ({ request }) => {
    const response = await request.get('/health/ready');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('application/json');
    await expect(response).toBeOK();

    const document = await response.json();
    expect(document).toMatchObject({
      schema_version: 1,
      service: 'test-patterns',
      bind_host: '127.0.0.1',
      port: 4222,
      readiness_scope: 'local_development_surface',
      production_verified: false,
      ready: true,
      checks: {
        generator: 'ready',
        timing_calibrated: false,
      },
    });
    expect(document.instance_token).toBeUndefined();
    expect(document.instance_token_sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(document.checks.sample_sha256).toHaveLength(3);
  });

  test('Playwright lifecycle owns and verifies the complete service block', async ({ request }) => {
    const services = [
      { port: 4220, service: 'evaluation' },
      { port: 4221, service: 'revenuecat-webhook' },
      { port: 4222, service: 'test-patterns' },
      { port: 4223, service: 'artifacts' },
    ];
    const identities = new Set<string>();
    for (const expected of services) {
      const response = await request.get(`http://127.0.0.1:${expected.port}/health/ready`);
      expect(response.status()).toBe(200);
      const document = await response.json();
      expect(document).toMatchObject({
        schema_version: 1,
        service: expected.service,
        bind_host: '127.0.0.1',
        port: expected.port,
        ready: true,
        production_verified: false,
      });
      expect(document.instance_token).toBeUndefined();
      expect(document.instance_token_sha256).toMatch(/^[0-9a-f]{64}$/);
      identities.add(document.instance_token_sha256);
    }
    expect(identities.size).toBe(services.length);
  });

  test('index exposes only original patterns and calibration limitations', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('Original capture test patterns');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Original capture test patterns',
    );
    await expect(page.getByRole('link', { name: /flicker field/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /moiré line target/i })).toBeVisible();
    await expect(page.getByText(/not a calibrated source measurement/i)).toBeVisible();
  });

  test('flicker surface states requested timing is not calibrated', async ({ page }) => {
    await page.goto('/patterns/flicker?hz=60&duty=0.5');
    await expect(page.getByRole('status')).toContainText('Requested square wave: 60 Hz');
    await expect(page.getByRole('status')).toContainText('not calibrated');
  });

  test('out-of-range timing is refused with a stable error', async ({ request }) => {
    const response = await request.get('/patterns/flicker?hz=500');
    expect(response.status()).toBe(400);
    await expect(response.json()).resolves.toMatchObject({
      schema_version: 1,
      service: 'test-patterns',
      error: { code: 'invalid_request' },
    });
  });
});
