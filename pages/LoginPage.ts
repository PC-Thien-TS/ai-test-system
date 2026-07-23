import { expect, type Page, type Request } from '@playwright/test';

type LoginOptions = {
  roleCode?: string;
};

type MacServiceState = {
  started: boolean;
  method?: string;
  url?: string;
  responseStatus?: number;
  responseHeaders?: Record<string, string | undefined>;
  failureErrorText?: string;
  succeeded: boolean;
  hasCorsOrPnaError: boolean;
  consoleErrors: string[];
  pageErrors: string[];
};

type MacServiceRequestRecord = {
  requestNumber: number;
  startedAt: number;
  method: string;
  url: string;
  responseStatus?: number;
  responseHeaders?: Record<string, string | undefined>;
  finishedAt?: number;
  elapsedMs?: number;
  requestFailedAt?: number;
  requestFailedElapsedMs?: number;
  requestFailedErrorText?: string;
  requestFinished: boolean;
};

export class LoginPage {
  private readonly loginNetworkEvents: string[] = [];
  private readonly pendingLoginRequests = new Map<Request, string>();
  private readonly macRequestRecords = new Map<Request, MacServiceRequestRecord>();
  private macRequestSequence = 0;
  private diagnosticsAttached = false;
  private macServiceState: MacServiceState = this.createMacServiceState();

  constructor(private readonly page: Page) {}

  async open() {
    this.captureLoginNetworkDiagnostics();
    await this.page.goto('/login');
    await expect(this.page.getByRole('textbox', { name: 'Tên tài khoản' })).toBeEditable();
  }

  async login(username: string, password: string, company: string, branch: string, options: LoginOptions = {}) {
    this.logDiagnostic('Login context', {
      roleCode: options.roleCode ?? 'standalone',
      hasUsername: Boolean(username),
      hasPassword: Boolean(password),
      company,
      branch,
    });

    const usernameInput = this.page.getByRole('textbox', { name: 'Tên tài khoản' });
    const passwordInput = this.page.getByRole('textbox', { name: 'Mật khẩu' });

    await usernameInput.fill(username);
    await passwordInput.fill(password);

    await expect(usernameInput, 'Username textbox should have a value after fill').not.toHaveValue('');
    await expect(passwordInput, 'Password textbox should have a value after fill').not.toHaveValue('');
    this.logDiagnostic('Credentials filled', {
      usernameTextboxHasValue: true,
      passwordTextboxHasValue: true,
    });

    await this.selectComboboxOption('Chọn công ty', company);
    await this.selectComboboxOption('Chọn phòng khám', branch);

    const loginButton = this.page.getByRole('button', { name: 'Đăng nhập' });
    await expect(loginButton, 'Login button should be enabled before submit').toBeEnabled();

    await loginButton.click();
    await this.waitForLoginResult();
  }

  async verifyLoginSuccess(branch: string) {
    await expect(this.page).not.toHaveURL(/\/login(?:[/?#]|$)/);
    await expect(this.page.getByText(branch, { exact: true })).toBeVisible();
  }

  private async selectComboboxOption(label: string, optionName: string) {
    const combobox = this.page.getByRole('combobox', { name: label });
    await combobox.click();

    const listbox = this.page.getByRole('listbox', { name: label });
    await expect(listbox, `Dropdown "${label}" should be open`).toBeVisible();

    const option = listbox.getByRole('option', { name: optionName, exact: true });
    await expect(
      option,
      `Option "${optionName}" should be available in dropdown "${label}". Check the test account data if it is missing.`,
    ).toBeVisible();

    await option.click();
    await expect
      .poll(async () => this.getLocatorDisplayValue(combobox), {
        timeout: 5000,
        message: `Combobox "${label}" should show selected option "${optionName}"`,
      })
      .toBe(optionName);
    this.logDiagnostic('Combobox selected', { label, optionName });
  }

  private async getLocatorDisplayValue(locator: ReturnType<Page['locator']>) {
    return locator.evaluate((element) => {
      if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
        return element.value.trim();
      }

      return (element.textContent ?? '').trim();
    });
  }

  private async waitForLoginResult() {
    const timeoutMs = 30000;
    const result = await Promise.race([
      this.page
        .waitForURL((url) => !this.isLoginUrl(url), { timeout: timeoutMs })
        .then(() => ({ type: 'success' as const }))
        .catch(() => this.neverResolve()),
      this.waitForLoginErrors(timeoutMs)
        .then((messages) => ({ type: 'error' as const, messages }))
        .catch(() => this.neverResolve()),
      this.resolveAfter(timeoutMs, async () => ({
        type: 'timeout' as const,
        messages: await this.collectLoginMessages(),
      })),
    ]);

    this.logDiagnostic('URL after login submit', { url: this.page.url() });

    if (result.type === 'error') {
      throw new Error(`Login failed with message: ${result.messages.join(' | ')}`);
    }

    if (result.type === 'timeout') {
      const macServiceClassification = this.classifyMacAddressService();

      if (macServiceClassification === 'network-unavailable') {
        throw new Error('Ứng dụng 315 MAC Address chưa chạy hoặc local service chưa sẵn sàng.');
      }

      if (macServiceClassification === 'cors-or-pna') {
        throw new Error(
          'Trình duyệt không được phép truy cập dịch vụ 315 MAC Address do CORS hoặc Private Network Access.',
        );
      }

      if (macServiceClassification === 'http-error') {
        throw new Error(
          `Dịch vụ 315 MAC Address trả HTTP ${this.macServiceState.responseStatus}. ${JSON.stringify(
            this.getSafeMacServiceDiagnostics(),
          )}`,
        );
      }

      const messageSuffix = result.messages.length
        ? ` Visible login messages: ${result.messages.join(' | ')}`
        : ' No visible login error message was found.';
      const networkSuffix = this.loginNetworkEvents.length
        ? ` Network diagnostics: ${this.loginNetworkEvents.join(' | ')}`
        : ' No failed or non-2xx/3xx login network responses were captured.';
      const pendingRequests = [...this.pendingLoginRequests.values()];
      const pendingSuffix = pendingRequests.length
        ? ` Pending requests: ${pendingRequests.join(' | ')}`
        : ' No pending requests were captured.';
      const macSuffix = ` 315 MAC Address diagnostics: ${JSON.stringify(this.getSafeMacServiceDiagnostics())}.`;

      if (macServiceClassification === 'pending') {
        throw new Error(
          `Request tới http://localhost:3153/system-info vẫn pending sau 30000ms. Không kết luận dịch vụ 315 MAC Address chưa chạy.${macSuffix}`,
        );
      }

      if (macServiceClassification === 'success') {
        throw new Error(
          `Dịch vụ 315 MAC Address đã trả HTTP 200, nhưng login API hoặc UI không hoàn tất trong 30000ms.${messageSuffix} ${networkSuffix} ${pendingSuffix}${macSuffix}`,
        );
      }

      throw new Error(
        `Login did not finish within 30000ms and URL is still ${this.page.url()}.${messageSuffix} ${networkSuffix} ${pendingSuffix}${macSuffix}`,
      );
    }
  }

  private async waitForLoginErrors(timeout: number) {
    await expect
      .poll(async () => (await this.collectLoginMessages()).length, {
        timeout,
        intervals: [250, 500, 1000],
        message: 'Wait for visible login error message',
      })
      .toBeGreaterThan(0);

    return this.collectLoginMessages();
  }

  private async neverResolve(): Promise<never> {
    return new Promise(() => {});
  }

  private async resolveAfter<T>(timeout: number, getValue: () => Promise<T>): Promise<T> {
    return new Promise((resolve) => {
      setTimeout(() => {
        void getValue().then(resolve);
      }, timeout);
    });
  }

  private async collectLoginMessages() {
    const selectors = [
      '[role="alert"]',
      '.Toastify__toast',
      '.toast',
      '.ant-message',
      '.ant-notification',
      '.MuiAlert-root',
      '.MuiFormHelperText-root',
      '.text-danger',
      '.error',
    ];

    const messages = new Set<string>();

    for (const selector of selectors) {
      const texts = await this.page.locator(selector).allTextContents();

      for (const text of texts) {
        const normalized = text.replace(/\s+/g, ' ').trim();

        if (normalized) {
          messages.add(normalized);
        }
      }
    }

    return [...messages];
  }

  private isLoginUrl(url: URL) {
    return /\/login(?:[/?#]|$)/.test(url.toString());
  }

  private logDiagnostic(message: string, data: Record<string, unknown>) {
    console.log(`[LoginPage] ${message}: ${JSON.stringify(data)}`);
  }

  private captureLoginNetworkDiagnostics() {
    this.loginNetworkEvents.length = 0;
    this.pendingLoginRequests.clear();
    this.macRequestRecords.clear();
    this.macRequestSequence = 0;
    this.macServiceState = this.createMacServiceState();

    if (this.diagnosticsAttached) {
      return;
    }

    this.diagnosticsAttached = true;
    this.page.on('request', (request) => {
      this.pendingLoginRequests.set(request, `${request.method()} ${request.url()}`);

      if (this.isSystemInfoUrl(request.url())) {
        const requestNumber = ++this.macRequestSequence;
        const startedAt = Date.now();
        const record: MacServiceRequestRecord = {
          requestNumber,
          startedAt,
          method: request.method(),
          url: request.url(),
          requestFinished: false,
        };

        this.macRequestRecords.set(request, record);
        this.macServiceState.started = true;
        this.macServiceState.method = request.method();
        this.macServiceState.url = request.url();
        this.logDiagnostic('315 MAC Address request started', {
          requestNumber,
          startedAt,
          method: request.method(),
          url: request.url(),
        });
      }
    });

    this.page.on('requestfinished', (request) => {
      this.pendingLoginRequests.delete(request);

      if (this.isSystemInfoUrl(request.url())) {
        const record = this.macRequestRecords.get(request);
        const finishedAt = Date.now();

        if (record) {
          record.finishedAt = finishedAt;
          record.elapsedMs = finishedAt - record.startedAt;
          record.requestFinished = true;
        }

        this.logDiagnostic('315 MAC Address request finished', {
          requestNumber: record?.requestNumber,
          finishedAt,
          elapsedMs: record?.elapsedMs,
          method: request.method(),
          url: request.url(),
        });
      }
    });

    this.page.on('requestfailed', (request) => {
      this.pendingLoginRequests.delete(request);
      const failureErrorText = request.failure()?.errorText ?? '';

      if (this.isSystemInfoUrl(request.url())) {
        const record = this.macRequestRecords.get(request);
        const requestFailedAt = Date.now();

        if (record) {
          record.requestFailedAt = requestFailedAt;
          record.requestFailedElapsedMs = requestFailedAt - record.startedAt;
          record.requestFailedErrorText = failureErrorText;
        }

        this.macServiceState.started = true;
        this.macServiceState.method = request.method();
        this.macServiceState.url = request.url();
        this.macServiceState.failureErrorText = failureErrorText;
        this.logDiagnostic('315 MAC Address request failed', {
          requestNumber: record?.requestNumber,
          requestFailedAt,
          elapsedMs: record?.requestFailedElapsedMs,
          method: request.method(),
          url: request.url(),
          errorText: failureErrorText,
        });
      }

      this.loginNetworkEvents.push(
        `request failed ${request.method()} ${request.url()} ${failureErrorText}`.trim(),
      );
    });

    this.page.on('response', (response) => {
      if (this.isSystemInfoUrl(response.url())) {
        const request = response.request();
        const record = this.macRequestRecords.get(request);
        const headers = response.headers();
        const responseHeaders = {
          'access-control-allow-origin': headers['access-control-allow-origin'],
          'access-control-allow-private-network': headers['access-control-allow-private-network'],
          'access-control-allow-methods': headers['access-control-allow-methods'],
          'access-control-allow-headers': headers['access-control-allow-headers'],
        };

        if (record) {
          record.responseStatus = response.status();
          record.responseHeaders = responseHeaders;
        }

        this.macServiceState.started = true;
        this.macServiceState.method = response.request().method();
        this.macServiceState.url = response.url();
        this.macServiceState.responseStatus = response.status();
        this.macServiceState.responseHeaders = responseHeaders;
        this.macServiceState.succeeded = response.status() === 200;
        this.logDiagnostic('315 MAC Address response', {
          requestNumber: record?.requestNumber,
          method: response.request().method(),
          url: response.url(),
          status: response.status(),
          corsHeaders: responseHeaders,
        });
      }

      if (response.status() >= 400) {
        this.loginNetworkEvents.push(
          `response ${response.status()} ${response.request().method()} ${response.url()}`,
        );
      }
    });

    this.page.on('console', (message) => {
      if (message.type() !== 'error') {
        return;
      }

      const text = message.text();
      this.macServiceState.consoleErrors.push(text);

      if (this.isCorsOrPnaText(text)) {
        this.macServiceState.hasCorsOrPnaError = true;
        this.logDiagnostic('Browser console CORS/PNA error', { text });
      } else {
        this.logDiagnostic('Browser console error', { text });
      }
    });

    this.page.on('pageerror', (error) => {
      const text = error.message;
      this.macServiceState.pageErrors.push(text);
      this.logDiagnostic('Browser page error', { text });
    });
  }

  private classifyMacAddressService() {
    if (this.macServiceState.hasCorsOrPnaError || this.isCorsOrPnaText(this.macServiceState.failureErrorText ?? '')) {
      return 'cors-or-pna';
    }

    if (this.macServiceState.failureErrorText && this.isConnectionFailure(this.macServiceState.failureErrorText)) {
      return 'network-unavailable';
    }

    if (this.getMacRequestRecords().some((record) => record.responseStatus !== undefined && record.responseStatus >= 400)) {
      return 'http-error';
    }

    if ([...this.pendingLoginRequests.keys()].some((request) => this.isSystemInfoUrl(request.url()))) {
      return 'pending';
    }

    if (this.macServiceState.succeeded) {
      return 'success';
    }

    if (this.getMacRequestRecords().some((record) => record.responseStatus === 200)) {
      return 'success';
    }

    if (this.macServiceState.started) {
      return 'unknown';
    }

    return 'not-requested';
  }

  private createMacServiceState(): MacServiceState {
    return {
      started: false,
      succeeded: false,
      hasCorsOrPnaError: false,
      consoleErrors: [],
      pageErrors: [],
    };
  }

  private getSafeMacServiceDiagnostics() {
    return {
      classification: this.classifyMacAddressService(),
      started: this.macServiceState.started,
      method: this.macServiceState.method,
      url: this.macServiceState.url,
      responseStatus: this.macServiceState.responseStatus,
      responseHeaders: this.macServiceState.responseHeaders,
      failureErrorText: this.macServiceState.failureErrorText,
      succeeded: this.macServiceState.succeeded,
      hasCorsOrPnaError: this.macServiceState.hasCorsOrPnaError,
      requests: this.getMacRequestRecords(),
      consoleErrors: this.macServiceState.consoleErrors,
      pageErrors: this.macServiceState.pageErrors,
    };
  }

  private getMacRequestRecords() {
    const now = Date.now();

    return [...this.macRequestRecords.values()].map((record) => ({
      requestNumber: record.requestNumber,
      startedAt: record.startedAt,
      method: record.method,
      url: record.url,
      responseStatus: record.responseStatus,
      responseHeaders: record.responseHeaders,
      finishedAt: record.finishedAt,
      elapsedMs: record.elapsedMs ?? now - record.startedAt,
      requestfailedErrorText: record.requestFailedErrorText,
      requestFinished: record.requestFinished,
    }));
  }

  private isSystemInfoUrl(url: string) {
    return /^http:\/\/localhost:3153\/system-info(?:[?#].*)?$/.test(url);
  }

  private isConnectionFailure(errorText: string) {
    return /ERR_CONNECTION_REFUSED|ERR_CONNECTION_RESET|ERR_CONNECTION_CLOSED|ERR_ADDRESS_UNREACHABLE|ERR_NAME_NOT_RESOLVED/i.test(
      errorText,
    );
  }

  private isCorsOrPnaText(text: string) {
    return /CORS|Cross-Origin|Private Network Access|preflight|Access-Control-Allow|ERR_FAILED/i.test(text);
  }
}
