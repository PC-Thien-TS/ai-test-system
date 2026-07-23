import { test } from '../../utils/test';
import { authenticateRole } from '../../utils/auth-role';

test('authenticate N03', async ({ page }) => {
  await authenticateRole(page, 'N03');
});
