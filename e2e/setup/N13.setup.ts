import { test } from '../../utils/test';
import { authenticateRole } from '../../utils/auth-role';

test('authenticate N13', async ({ page }) => {
  await authenticateRole(page, 'N13');
});
