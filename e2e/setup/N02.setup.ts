import { test } from '../../utils/test';
import { authenticateRole } from '../../utils/auth-role';

test('authenticate N02', async ({ page }) => {
  await authenticateRole(page, 'N02');
});
