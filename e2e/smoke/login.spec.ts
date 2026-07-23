import { test } from '../../utils/test';
import { LoginPage } from '../../pages/LoginPage';

test.use({ storageState: undefined });

function getRequiredEnv(name: string) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

test('AUT-001 - Đăng nhập thành công', async ({ page }) => {
  const username = getRequiredEnv('TEST_USERNAME');
  const password = getRequiredEnv('TEST_PASSWORD');
  const company = getRequiredEnv('TEST_COMPANY');
  const branch = getRequiredEnv('TEST_BRANCH');
  const loginPage = new LoginPage(page);

  await test.step('Mở trang đăng nhập', async () => {
    await loginPage.open();
  });

  await test.step('Nhập thông tin đăng nhập', async () => {
    await loginPage.login(username, password, company, branch);
  });

  await test.step('Kiểm tra đăng nhập thành công', async () => {
    await loginPage.verifyLoginSuccess(branch);
  });
});
