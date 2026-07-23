import { expect, test as base } from '@playwright/test';

const localNetworkPermissions = ['local-network-access'];

function getApplicationOrigin(baseURL?: string) {
  const url = baseURL ?? process.env.BASE_URL;

  if (!url) {
    throw new Error('Missing BASE_URL for local network permission grant.');
  }

  return new URL(url).origin;
}

export const test = base.extend<{ grantLocalNetworkAccess: void }>({
  grantLocalNetworkAccess: [
    async ({ context, baseURL }, use) => {
      const origin = getApplicationOrigin(baseURL);

      await context.grantPermissions(localNetworkPermissions, { origin });
      console.log(
        `[permissions] Granted ${localNetworkPermissions.join(', ')} to ${origin}`,
      );

      await use();
    },
    { auto: true },
  ],
});

export { expect };
