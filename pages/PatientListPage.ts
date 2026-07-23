import { expect, type Page } from '@playwright/test';

export class PatientListPage {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto('/', {
      waitUntil: 'commit',
      timeout: 15_000,
    });

    const systemMenu = this.page.getByRole('menuitem', {
      name: 'Hệ thống',
    });

    await expect(systemMenu).toBeVisible({
      timeout: 30_000,
    });
    await systemMenu.click();

    await this.page
      .getByRole('menuitem', { name: 'Tra cứu' })
      .click();

    await this.page
      .getByRole('link', { name: 'Bệnh nhân' })
      .click();

    await expect(this.page).toHaveURL(
      /\/tracuu\/benhnhanh\/?$/,
      { timeout: 20_000 },
    );
  }

  async search(): Promise<void> {
    await this.page.getByRole('button', { name: /Tìm/i }).click();
  }

  async expectPatientTableVisible(): Promise<void> {
    await expect(
      this.page.getByRole('columnheader', {
        name: 'Mã bệnh nhân',
        exact: true,
      }),
    ).toBeVisible();

    await expect(
      this.page.getByRole('columnheader', {
        name: 'Tên bệnh nhân',
        exact: true,
      }),
    ).toBeVisible();
  }
}
