# Playwright Authentication Preconditions

Before running login, setup, or role-session tests against `https://devmeta.315healthcare.com`, open the real **315 MAC Address** application on the test machine.

The web application calls the local service:

```text
http://localhost:3153/system-info
```

This service is a real authentication precondition. Do not mock or fulfill it in Playwright. If the service is not running or is not ready, authentication can stay on `/login` and the test will fail with:

```text
Ứng dụng 315 MAC Address chưa chạy hoặc local service chưa sẵn sàng.
```

Run the role setup only after the local service is available:

```powershell
npx.cmd playwright test e2e/setup/N13.setup.ts --project=setup-N13 --headed
```
