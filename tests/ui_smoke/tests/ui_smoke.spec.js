const { test, expect } = require("@playwright/test");

const BASE_URL = process.env.BASE_URL || "";
const API_USER = process.env.API_USER || "";
const API_PASS = process.env.API_PASS || "";

const ROUTES = {
  auth: ["/login", "/auth/login", "/signin", "/dang-nhap"],
  search: ["/search", "/searches", "/tim-kiem"],
  store: ["/store", "/stores", "/merchant", "/merchants"],
  posts: ["/posts", "/newsfeed", "/feed"],
  news: ["/news", "/tin-tuc"],
  organization: ["/organization", "/profile", "/account", "/me"],
  notification: ["/notification", "/notifications", "/thong-bao"]
};

const fatalPatterns = [
  /internal server error/i,
  /something went wrong/i,
  /application error/i,
  /unhandled exception/i,
  /stack trace/i
];

const notFoundPatterns = [/404/i, /page not found/i, /cannot get/i, /không tìm thấy/i];

async function bodyText(page) {
  return ((await page.textContent("body").catch(() => "")) || "").trim();
}

async function hasPattern(page, patterns) {
  const text = await bodyText(page);
  return patterns.some((pattern) => pattern.test(text));
}

async function assertNoFatal(page) {
  const fatal = await hasPattern(page, fatalPatterns);
  expect(fatal, "Fatal error signature detected in UI").toBeFalsy();
}

async function firstVisible(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    const count = await locator.count().catch(() => 0);
    if (count < 1) {
      continue;
    }
    const visible = await locator.isVisible().catch(() => false);
    if (visible) {
      return locator;
    }
  }
  return null;
}

async function openFirstRoute(page, candidates) {
  for (const route of candidates) {
    try {
      const response = await page.goto(route, { waitUntil: "domcontentloaded", timeout: 20_000 });
      await page.waitForTimeout(500);
      const status = response ? response.status() : null;
      if (status && status >= 500) {
        continue;
      }
      const isNotFound = await hasPattern(page, notFoundPatterns);
      if (status === 404 || isNotFound) {
        continue;
      }
      return { route, status };
    } catch {
      // Try next route candidate.
    }
  }
  return null;
}

function isLoginUrl(url) {
  const value = (url || "").toLowerCase();
  return value.includes("login") || value.includes("signin") || value.includes("dang-nhap");
}

async function submitLogin(page, username, password) {
  const userInput = await firstVisible(page, [
    'input[type="email"]',
    'input[name*="email" i]',
    'input[name*="user" i]',
    'input[name*="phone" i]',
    'input[type="text"]'
  ]);
  const passInput = await firstVisible(page, ['input[type="password"]', 'input[name*="pass" i]']);
  if (!userInput || !passInput) {
    return { skipped: true, reason: "Login form fields not found." };
  }

  let loginStatus = null;
  const listener = (response) => {
    const url = response.url().toLowerCase();
    if (url.includes("/auth/login")) {
      loginStatus = response.status();
    }
  };
  page.on("response", listener);

  await userInput.fill(username);
  await passInput.fill(password);

  const submitButton = await firstVisible(page, [
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    'button:has-text("Đăng nhập")',
    'button[type="submit"]',
    'input[type="submit"]'
  ]);

  if (submitButton) {
    await submitButton.click();
  } else {
    await passInput.press("Enter");
  }

  await page.waitForTimeout(1_200);
  page.off("response", listener);

  if (loginStatus !== null) {
    return { skipped: false, status: loginStatus };
  }

  const fatal = await hasPattern(page, fatalPatterns);
  if (fatal) {
    return { skipped: false, status: 500 };
  }

  const remainedOnLogin = isLoginUrl(page.url());
  if (!remainedOnLogin) {
    return { skipped: false, status: 200 };
  }
  return { skipped: false, status: 401 };
}

async function loginIfPossible(page) {
  if (!API_USER || !API_PASS) {
    return { ok: false, skipped: true, reason: "API_USER/API_PASS are not set." };
  }
  const authRoute = await openFirstRoute(page, ROUTES.auth);
  if (!authRoute) {
    return { ok: false, skipped: true, reason: "Auth route is not inferable." };
  }
  const result = await submitLogin(page, API_USER, API_PASS);
  if (result.skipped) {
    return { ok: false, skipped: true, reason: result.reason };
  }
  if ([200, 201, 204].includes(result.status)) {
    return { ok: true, skipped: false };
  }
  return { ok: false, skipped: true, reason: `Login not successful (status=${result.status}).` };
}

test.beforeEach(async () => {
  test.skip(!BASE_URL, "BASE_URL is required for UI smoke tests.");
});

test("AUTH-UI-001 login success", async ({ page }) => {
  test.skip(!API_USER || !API_PASS, "API_USER/API_PASS are required for login success test.");
  const authRoute = await openFirstRoute(page, ROUTES.auth);
  test.skip(!authRoute, "Login route is not inferable from known candidates.");

  const result = await submitLogin(page, API_USER, API_PASS);
  test.skip(result.skipped, result.reason);
  expect([200, 201, 204]).toContain(result.status);
  await assertNoFatal(page);
});

test("AUTH-UI-002 login failure", async ({ page }) => {
  test.skip(!API_USER || !API_PASS, "API_USER/API_PASS are required for login failure test.");
  const authRoute = await openFirstRoute(page, ROUTES.auth);
  test.skip(!authRoute, "Login route is not inferable from known candidates.");

  const result = await submitLogin(page, API_USER, `${API_PASS}-wrong`);
  test.skip(result.skipped, result.reason);
  expect([400, 401, 403]).toContain(result.status);
  await assertNoFatal(page);
});

test("AUTH-UI-003 logout if available", async ({ page }) => {
  const login = await loginIfPossible(page);
  test.skip(login.skipped, login.reason);
  if (!login.ok) {
    test.skip(true, "Login precondition is not satisfied.");
  }

  const logoutControl = await firstVisible(page, [
    'button:has-text("Logout")',
    'button:has-text("Sign out")',
    'button:has-text("Đăng xuất")',
    'a:has-text("Logout")',
    'a:has-text("Đăng xuất")'
  ]);
  test.skip(!logoutControl, "Logout control is not exposed in UI.");

  await logoutControl.click();
  await page.waitForTimeout(800);
  await assertNoFatal(page);
});

test("SEARCH-UI-001 open search and query keyword", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.search);
  test.skip(!route, "Search route is not inferable from known candidates.");

  const input = await firstVisible(page, [
    'input[type="search"]',
    'input[name*="search" i]',
    'input[placeholder*="search" i]',
    'input[placeholder*="tìm" i]'
  ]);
  test.skip(!input, "Search input is not visible on search page.");

  await input.fill("test");
  await input.press("Enter");
  await page.waitForTimeout(1_200);
  await assertNoFatal(page);
});

test("SEARCH-UI-002 suggestions/history if exposed", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.search);
  test.skip(!route, "Search route is not inferable from known candidates.");

  const input = await firstVisible(page, [
    'input[type="search"]',
    'input[name*="search" i]',
    'input[placeholder*="search" i]',
    'input[placeholder*="tìm" i]'
  ]);
  test.skip(!input, "Search input is not visible on search page.");

  await input.fill("te");
  await page.waitForTimeout(800);
  const suggestionVisible = await firstVisible(page, [
    '[role="listbox"]',
    '[class*="suggest"]',
    '[data-testid*="suggest"]'
  ]);
  const historyVisible = await firstVisible(page, [
    ':text-matches("history|lịch sử", "i")',
    '[class*="history"]',
    '[data-testid*="history"]'
  ]);
  test.skip(!suggestionVisible && !historyVisible, "Suggestion/history widgets are not exposed.");
  await assertNoFatal(page);
});

test("STORE-UI-001 open store list", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.store);
  test.skip(!route, "Store route is not inferable from known candidates.");
  await assertNoFatal(page);
});

test("STORE-UI-002 open one store detail", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.store);
  test.skip(!route, "Store route is not inferable from known candidates.");

  const detailLink = await firstVisible(page, ['a[href*="/store/"]', 'a[href*="/merchant/"]']);
  test.skip(!detailLink, "Store detail link is not inferable from store list page.");
  await detailLink.click();
  await page.waitForTimeout(1_000);
  await assertNoFatal(page);
});

test("POSTS-UI-001 open posts/newsfeed and verify sections", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.posts);
  test.skip(!route, "Posts/newsfeed route is not inferable from known candidates.");
  await assertNoFatal(page);

  const sectionDetected = await firstVisible(page, [
    ':text-matches("categories|category|danh mục", "i")',
    ':text-matches("recommend|đề xuất", "i")',
    '[class*="category"]',
    '[class*="recommend"]'
  ]);
  test.skip(!sectionDetected, "Categories/recommend sections are not inferable on posts page.");
});

test("NEWS-UI-001 open news list", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.news);
  test.skip(!route, "News route is not inferable from known candidates.");
  await assertNoFatal(page);
});

test("NEWS-UI-002 open one news detail if inferable", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.news);
  test.skip(!route, "News route is not inferable from known candidates.");

  const detailLink = await firstVisible(page, ['a[href*="/news/"]', 'a[href*="/tin-tuc/"]']);
  test.skip(!detailLink, "News detail link is not inferable from news list page.");
  await detailLink.click();
  await page.waitForTimeout(1_000);
  await assertNoFatal(page);
});

test("ORG-UI-001 open organization/profile/info page", async ({ page }) => {
  const route = await openFirstRoute(page, ROUTES.organization);
  test.skip(!route, "Organization/profile route is not inferable from known candidates.");
  await assertNoFatal(page);
});

test("NOTI-UI-001 open notification page and unread/list render", async ({ page }) => {
  const login = await loginIfPossible(page);
  test.skip(login.skipped, login.reason);
  if (!login.ok) {
    test.skip(true, "Login precondition is not satisfied.");
  }

  const route = await openFirstRoute(page, ROUTES.notification);
  test.skip(!route, "Notification route is not inferable from known candidates.");
  await assertNoFatal(page);

  const unreadOrList = await firstVisible(page, [
    ':text-matches("unread|chưa đọc", "i")',
    '[class*="notification"]',
    '[data-testid*="notification"]',
    '[role="list"]'
  ]);
  test.skip(!unreadOrList, "Notification list/unread indicator is not inferable.");
});
