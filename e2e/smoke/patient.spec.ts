import { test } from '../../utils/test';
import { PatientListPage } from '../../pages/PatientListPage';

test.setTimeout(60_000);

test(
  'PAT-001 - Tra cứu danh sách bệnh nhân @smoke @patient @P0',
  async ({ page }) => {
    const patientListPage = new PatientListPage(page);

    await test.step('Mở màn hình danh sách bệnh nhân', async () => {
      await patientListPage.open();
    });

    await test.step('Tìm kiếm danh sách bệnh nhân', async () => {
      await patientListPage.search();
    });

    await test.step('Kiểm tra bảng bệnh nhân hiển thị', async () => {
      await patientListPage.expectPatientTableVisible();
    });
  },
);
