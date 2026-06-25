/**
 * Critical user journey E2E tests for HFB platform.
 *
 * These tests verify the most important flows:
 * 1. Home page loads and shows system status
 * 2. Navigation works across all main pages
 * 3. Search functionality
 * 4. Book browsing
 * 5. Auth flow (login)
 *
 * Run: npx playwright test
 */
import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('loads and shows title', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=皇甫谧数字人文平台')).toBeVisible();
  });

  test('navigation links are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('text=古籍库')).toBeVisible();
    await expect(page.locator('text=人物')).toBeVisible();
    await expect(page.locator('text=知识图谱')).toBeVisible();
    await expect(page.locator('text=搜索')).toBeVisible();
  });
});

test.describe('Navigation', () => {
  test('navigates to Books page', async ({ page }) => {
    await page.goto('/');
    await page.click('text=古籍库');
    await expect(page).toHaveURL(/\/books/);
  });

  test('navigates to Persons page', async ({ page }) => {
    await page.goto('/');
    await page.click('text=人物');
    await expect(page).toHaveURL(/\/persons/);
  });

  test('navigates to Search page', async ({ page }) => {
    await page.goto('/');
    await page.click('a:has-text("搜索")');
    await expect(page).toHaveURL(/\/search/);
  });

  test('navigates to Knowledge Graph page', async ({ page }) => {
    await page.goto('/');
    await page.click('text=知识图谱');
    await expect(page).toHaveURL(/\/graph/);
  });

  test('navigates to Dashboard page', async ({ page }) => {
    await page.goto('/');
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });
});

test.describe('Search', () => {
  test('search input is visible', async ({ page }) => {
    await page.goto('/search');
    await expect(page.locator('input[placeholder*="搜索"]')).toBeVisible();
  });

  test('entity type filters are present', async ({ page }) => {
    await page.goto('/search');
    await expect(page.locator('button:has-text("人物")').first()).toBeVisible();
    await expect(page.locator('button:has-text("古籍库")').first()).toBeVisible();
  });
});

test.describe('Book Browse', () => {
  test('book list page loads', async ({ page }) => {
    await page.goto('/books');
    await expect(page.locator('h1, h2, .page-title').first()).toBeVisible();
  });
});

test.describe('Auth', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="密码"]')).toBeVisible();
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="邮箱"]')).toBeVisible();
  });
});
