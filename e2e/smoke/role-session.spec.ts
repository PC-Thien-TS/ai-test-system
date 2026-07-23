import { expect, test } from '../../utils/test';
import { roles, type RoleCode } from '../../test-data/roles';
import { getRoleCredentials } from '../../utils/auth-role';

test('AUT-002 - Sử dụng lại phiên đăng nhập theo vai trò @smoke @auth', async ({ page }, testInfo) => {
  const roleCode = testInfo.project.name as RoleCode;
  const role = roles[roleCode];

  if (!role) {
    test.skip(true, `Project ${testInfo.project.name} is not a role project`);
    return;
  }

  const { branch } = getRoleCredentials(roleCode);

  await page.goto('/');

  await expect(page).not.toHaveURL(/\/login(?:[/?#]|$)/);
  await expect(page.getByText(branch, { exact: true })).toBeVisible();

  const roleText = page.getByText(role.name, { exact: true });

  if (await roleText.count()) {
    await expect(roleText.first()).toBeVisible();
  }
});
