import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

const job = 'We need a data analyst who uses Python and SQL to build reports, analyze trends, and communicate findings to the team.'
const resume = `Alex Morgan
alex@example.com | +1 202 555 0123
SUMMARY
Data analyst with Python and SQL experience.
EXPERIENCE
Built a weekly sales dashboard using Python and SQL for my team.
EDUCATION
Bachelor of Science in Computer Science.`

test('account, recruiter ranking, applicant analysis, PDF preview and saved work', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`
  await page.goto('/')
  await expect(page.getByRole('link', { name: /Get started/ }).first()).toBeVisible()
  await page.getByRole('link', { name: /Get started/ }).first().click()
  await page.getByLabel('Full name').fill('Alex Morgan')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: /Create account ↗/ }).click()
  await expect(page).toHaveURL(/\/choose/)
  await page.getByRole('button', { name: /Enter recruiter mode/ }).click()
  await expect(page).toHaveURL(/\/recruiter/)
  await page.getByLabel('Job description').fill(job)
  await page.locator('.file-field').filter({ hasText: 'Candidate CVs' }).locator('input[type=file]').setInputFiles({ name: 'alex.txt', mimeType: 'text/plain', buffer: Buffer.from(resume) })
  await page.getByRole('button', { name: /Rank candidates/ }).click()
  await expect(page.getByText('Shortlist, with receipts.')).toBeVisible()
  await expect(page.getByRole('listitem').filter({ hasText: 'Alex Morgan' })).toBeVisible()
  await page.getByRole('button', { name: /Applicant/ }).first().click()
  await expect(page).toHaveURL(/\/applicant/)
  await page.getByRole('tab', { name: 'Analyze & tailor' }).click()
  await page.getByLabel('Target job description').fill(job)
  await page.getByRole('textbox', { name: 'Your resume', exact: true }).fill(resume)
  await page.getByRole('button', { name: /Analyze my resume/ }).click()
  await expect(page.getByText('Review the proposed edits.')).toBeVisible()
  await page.getByRole('button', { name: /Build final draft/ }).click()
  await expect(page.getByTitle('Actual exported PDF preview')).toHaveAttribute('src', /^blob:/)
  await page.getByPlaceholder('e.g. Data analyst · November').fill('Analyst draft')
  await page.getByRole('button', { name: /Save version/ }).click()
  await expect(page.getByText('Resume version saved to your account.')).toBeVisible()
  await page.getByRole('tab', { name: 'Start' }).click()
  await expect(page.getByText('Analyst draft')).toBeVisible()
  await page.getByRole('button', { name: /Alex Morgan.*⌄/ }).click()
  await expect(page.getByRole('button', { name: 'Download my data ↓' })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out ↗' }).click()
  await expect(page).toHaveURL(/\/auth/)
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Sign in ↗' }).click()
  await expect(page).toHaveURL(/\/choose/)
  await page.getByRole('button', { name: /Enter applicant mode/ }).click()
  await page.getByRole('button', { name: /Alex Morgan.*⌄/ }).click()
  const downloading = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download my data ↓' }).click()
  const exported = await downloading
  expect(exported.suggestedFilename()).toBe('hireflow-account-data.json')
  expect(JSON.parse(readFileSync(await exported.path() as string, 'utf8')).resume_versions).toHaveLength(1)
  await page.getByRole('button', { name: 'Delete account →' }).click()
  await page.getByLabel('Current password').fill('password123')
  await page.getByLabel('Type DELETE to confirm').fill('DELETE')
  await page.getByRole('button', { name: 'Delete account', exact: true }).click()
  await expect(page).toHaveURL(/\/$/)
  await page.goto('/auth')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Sign in ↗' }).click()
  await expect(page.getByRole('alert')).toContainText('Email or password was not recognized')
})
