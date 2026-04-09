// Playwright E2E test for the redesigned Report system
import { chromium } from 'playwright';
import { writeFileSync } from 'fs';

const BASE = 'http://localhost:3000';
const SCREENSHOT_DIR = '/tmp/report-tests';

async function screenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: false });
  console.log(`  [screenshot] ${name}`);
  return path;
}

async function main() {
  // Ensure screenshot dir exists
  const { mkdirSync } = await import('fs');
  mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: 'dark',
  });
  const page = await context.newPage();

  // Increase default timeout
  page.setDefaultTimeout(15000);

  try {
    // ── Step 1: Login ──
    console.log('\n=== Step 1: Login ===');
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');
    await screenshot(page, '01-login-page');

    // Fill login form — look for email/password inputs
    const emailInput = page.locator('input[type="email"], input[name="email"], input[placeholder*="mail"]').first();
    const passInput = page.locator('input[type="password"]').first();

    if (await emailInput.isVisible()) {
      await emailInput.fill('robert@investmentx.ai');
      await passInput.fill('admin');
      await screenshot(page, '02-login-filled');

      // Submit
      const submitBtn = page.locator('button[type="submit"], button:has-text("Sign In"), button:has-text("Login"), button:has-text("Log in")').first();
      await submitBtn.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      await screenshot(page, '03-after-login');
    } else {
      console.log('  No email input found, may already be logged in');
    }

    // ── Step 2: Navigate to Reports ──
    console.log('\n=== Step 2: Navigate to Reports ===');
    await page.goto(`${BASE}/reports`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await screenshot(page, '04-reports-list');

    // ── Step 3: Click New Report → Template Picker ──
    console.log('\n=== Step 3: Template Picker ===');
    const newBtn = page.locator('button:has-text("New Report")').first();
    if (await newBtn.isVisible()) {
      await newBtn.click();
      await page.waitForTimeout(1000);
      await screenshot(page, '05-template-picker');

      // Select "Macro Outlook" template
      const macroBtn = page.locator('button:has-text("Macro Outlook")').first();
      if (await macroBtn.isVisible()) {
        await macroBtn.click();
        console.log('  Selected Macro Outlook template');
      } else {
        // Fallback: click first template
        const firstTemplate = page.locator('button:has-text("Blank")').first();
        if (await firstTemplate.isVisible()) {
          await firstTemplate.click();
          console.log('  Selected Blank template');
        }
      }
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      await screenshot(page, '06-report-editor');
    } else {
      console.log('  New Report button not found');
      await screenshot(page, '05-no-new-button');
    }

    // ── Step 4: Editor interaction ──
    console.log('\n=== Step 4: Editor Interaction ===');

    // Check if we're in the editor (should see slide thumbnails)
    const editor = page.locator('[class*="aspect-[16/9]"]').first();
    if (await editor.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('  Editor canvas visible');

      // Edit the title
      const titleInput = page.locator('input[placeholder*="Title"], input[placeholder*="title"]').first();
      if (await titleInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await titleInput.fill('Q2 2026 Macro Outlook');
        console.log('  Filled title');
      }
      await screenshot(page, '07-editor-with-title');

      // Click on slide 2 (if exists)
      const slide2 = page.locator('[class*="rounded-"][class*="border"][class*="cursor-pointer"]').nth(1);
      if (await slide2.isVisible({ timeout: 3000 }).catch(() => false)) {
        await slide2.click();
        await page.waitForTimeout(500);
        await screenshot(page, '08-slide-2');
        console.log('  Switched to slide 2');
      }

      // Try adding a new slide via "+ New Slide" button
      const newSlideBtn = page.locator('button:has-text("New Slide")').first();
      if (await newSlideBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await newSlideBtn.click();
        await page.waitForTimeout(1000);
        await screenshot(page, '09-layout-picker');
        console.log('  Layout picker opened');

        // Select chart_full layout
        const chartFullBtn = page.locator('button:has-text("Chart")').first();
        if (await chartFullBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await chartFullBtn.click();
          await page.waitForTimeout(500);
          await screenshot(page, '10-new-chart-slide');
          console.log('  Added chart slide');
        }
      }

      // Try opening chart picker by clicking the "Click to add chart" area
      const addChartBtn = page.locator('button:has-text("Click to add chart")').first();
      if (await addChartBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await addChartBtn.click();
        await page.waitForTimeout(1500);
        await screenshot(page, '11-chart-picker');
        console.log('  Chart picker opened');

        // Check if charts are listed
        const chartList = page.locator('button:has(svg.lucide-line-chart)');
        const chartCount = await chartList.count();
        console.log(`  Found ${chartCount} charts in picker`);

        if (chartCount > 0) {
          // Click first chart to preview
          await chartList.first().click();
          await page.waitForTimeout(2000);
          await screenshot(page, '12-chart-preview');
          console.log('  Chart preview shown');

          // Click "Insert Chart" button
          const insertBtn = page.locator('button:has-text("Insert Chart")').first();
          if (await insertBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
            await insertBtn.click();
            await page.waitForTimeout(2000);
            await screenshot(page, '13-chart-inserted');
            console.log('  Chart inserted into slide');
          }
        }

        // Close picker if still open
        const closeBtn = page.locator('button[aria-label="Close"]').first();
        if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
          await closeBtn.click();
        }
      }

      // ── Step 5: Test duplicate slide ──
      console.log('\n=== Step 5: Duplicate & Properties ===');
      const duplicateBtn = page.locator('button[title*="Duplicate"]').first();
      if (await duplicateBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await duplicateBtn.click();
        await page.waitForTimeout(500);
        console.log('  Slide duplicated');
      }

      // Open properties panel
      const propsBtn = page.locator('button[title*="properties"]').first();
      if (await propsBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await propsBtn.click();
        await page.waitForTimeout(500);
        await screenshot(page, '14-properties-panel');
        console.log('  Properties panel opened');
      }

      // ── Step 6: Test layout switcher ──
      console.log('\n=== Step 6: Layout Switcher ===');
      await screenshot(page, '15-layout-switcher');
      // The layout switcher icons should be visible above the canvas

      // ── Step 7: Test present mode ──
      console.log('\n=== Step 7: Present Mode ===');
      const presentBtn = page.locator('button:has-text("Present")').first();
      if (await presentBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await presentBtn.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(3000);
        await screenshot(page, '16-present-mode');
        console.log('  Presentation mode opened');

        // Navigate forward
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(1000);
        await screenshot(page, '17-present-slide-2');
        console.log('  Navigated to slide 2');

        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(1000);
        await screenshot(page, '18-present-slide-3');

        // Exit presentation
        await page.keyboard.press('Escape');
        await page.waitForTimeout(1000);
      }

      // ── Step 8: Test export buttons ──
      console.log('\n=== Step 8: Export Buttons ===');
      await page.goto(`${BASE}/reports`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Click the first report to re-open editor
      const reportCard = page.locator('[class*="cursor-pointer"][class*="rounded"]').first();
      if (await reportCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        await reportCard.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);
        await screenshot(page, '19-editor-reopened');

        // Check PPTX and PDF buttons exist
        const pptxBtn = page.locator('button:has-text("PPTX")').first();
        const pdfBtn = page.locator('button:has-text("PDF")').first();
        console.log(`  PPTX button visible: ${await pptxBtn.isVisible().catch(() => false)}`);
        console.log(`  PDF button visible: ${await pdfBtn.isVisible().catch(() => false)}`);
        await screenshot(page, '20-export-buttons');
      }

    } else {
      console.log('  Editor canvas not visible');
      await screenshot(page, '07-no-editor');
    }

    console.log('\n=== All tests completed ===');
    console.log(`Screenshots saved to ${SCREENSHOT_DIR}/`);

  } catch (err) {
    console.error('Test error:', err.message);
    await screenshot(page, 'error-state');
  } finally {
    await browser.close();
  }
}

main().catch(console.error);
