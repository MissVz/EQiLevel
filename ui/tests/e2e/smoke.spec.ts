import { test, expect } from '@playwright/test'

test('SPA loads and navigates to Settings', async ({ page, baseURL }) => {
  const base = (baseURL || 'http://127.0.0.1:8000/web') + '/#/session'
  await page.goto(base)
  await expect(page.getByRole('heading', { name: 'Session' })).toBeVisible()
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  const apiInput = page.getByPlaceholder('http://127.0.0.1:8000')
  await expect(apiInput).toBeVisible()
})

test('Admin page renders and refresh works (no auth required for UI render)', async ({ page, baseURL }) => {
  await page.goto((baseURL || 'http://127.0.0.1:8000/web') + '/#/admin')
  await expect(page.getByRole('heading', { name: 'Admin' })).toBeVisible()
  await page.getByRole('button', { name: /Refresh/i }).click()
  // table renders (might be empty)
  await expect(page.getByText(/result\(s\)/i)).toBeVisible()
})

