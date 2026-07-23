import fs from 'fs';
import path from 'path';
import type { Page } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { roles, type RoleCode } from '../test-data/roles';

type RoleCredentials = {
  username: string;
  password: string;
  company: string;
  branch: string;
};

function getRequiredRoleEnv(roleCode: RoleCode, name: keyof RoleCredentials) {
  const envName = `${roleCode}_${name.toUpperCase()}`;
  const value = process.env[envName];

  if (!value) {
    throw new Error(`Missing required environment variable for role ${roleCode}: ${envName}`);
  }

  return value;
}

export function getRoleCredentials(roleCode: RoleCode): RoleCredentials {
  if (!roles[roleCode]) {
    throw new Error(`Unsupported role code: ${roleCode}`);
  }

  return {
    username: getRequiredRoleEnv(roleCode, 'username'),
    password: getRequiredRoleEnv(roleCode, 'password'),
    company: getRequiredRoleEnv(roleCode, 'company'),
    branch: getRequiredRoleEnv(roleCode, 'branch'),
  };
}

export function getRoleStorageStatePath(roleCode: RoleCode) {
  return path.join(process.cwd(), 'playwright', '.auth', `${roleCode}.json`);
}

export async function authenticateRole(page: Page, roleCode: RoleCode) {
  const credentials = getRoleCredentials(roleCode);
  const loginPage = new LoginPage(page);

  console.log(
    `[auth-role] Authenticating role ${roleCode}: ${JSON.stringify({
      hasUsername: Boolean(credentials.username),
      hasPassword: Boolean(credentials.password),
      company: credentials.company,
      branch: credentials.branch,
    })}`,
  );

  await loginPage.open();
  await loginPage.login(
    credentials.username,
    credentials.password,
    credentials.company,
    credentials.branch,
    { roleCode },
  );
  await loginPage.verifyLoginSuccess(credentials.branch);

  const storageStatePath = getRoleStorageStatePath(roleCode);
  fs.mkdirSync(path.dirname(storageStatePath), { recursive: true });
  await page.context().storageState({ path: storageStatePath });
}
