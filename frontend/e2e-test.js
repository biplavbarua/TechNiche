/**
 * TechNiche E2E Test Suite
 * Tests the full user journey from landing → submit → results
 * Also verifies the 3 patentable-claim features in the response JSON.
 */

const { chromium } = require("playwright");

const FRONTEND = "http://localhost:3000";
const BACKEND  = "http://localhost:8000";
const TIMEOUT  = 120_000; // 2 min – LLM cascade can be slow

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function checkBackendHealth() {
  const res = await fetch(`${BACKEND}/`);
  const data = await res.json();
  return data?.status?.includes("running");
}

async function runTests() {
  console.log("\n🚀 TechNiche E2E Test Suite\n" + "=".repeat(50));
  const results = [];

  // ── Backend health check ─────────────────────────────
  try {
    const healthy = await checkBackendHealth();
    results.push({ test: "Backend /  health check", pass: healthy });
    console.log(healthy ? "✅ Backend is healthy" : "❌ Backend health check failed");
  } catch (e) {
    results.push({ test: "Backend / health check", pass: false, error: e.message });
    console.log("❌ Backend unreachable:", e.message);
  }

  // ── Direct API smoke test ────────────────────────────
  let apiResult = null;
  try {
    console.log("\n📡 Calling /api/analyze directly...");
    const res = await fetch(`${BACKEND}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: "I want to build a music streaming app similar to Spotify for Indian artists" }),
      signal: AbortSignal.timeout(TIMEOUT),
    });
    apiResult = await res.json();

    const hasAnalysis   = typeof apiResult.analysis === "string" && apiResult.analysis.length > 100;
    const hasCited      = Array.isArray(apiResult.cited_cases);
    const hasVerif      = apiResult.citation_verification !== undefined;
    const hasRelevance  = ["high","low","none"].includes(apiResult.relevance_quality);

    results.push({ test: "API: analysis text returned",       pass: hasAnalysis });
    results.push({ test: "API: cited_cases array present",    pass: hasCited });
    results.push({ test: "API: citation_verification field",  pass: hasVerif });
    results.push({ test: "API: relevance_quality field",      pass: hasRelevance });

    console.log(hasAnalysis  ? "✅ Analysis text present"             : "❌ No analysis text");
    console.log(hasCited     ? "✅ cited_cases present"               : "❌ cited_cases missing");
    console.log(hasVerif     ? "✅ citation_verification present"     : "❌ citation_verification missing");
    console.log(hasRelevance ? "✅ relevance_quality present"         : "❌ relevance_quality missing");

    if (hasVerif) {
      const cv = apiResult.citation_verification;
      console.log(`   ↳ grounded: ${cv.grounded?.length ?? 0}, ungrounded: ${cv.ungrounded?.length ?? 0}, confidence: ${cv.confidence}, correction_applied: ${cv.correction_applied ?? false}`);
    }
    if (apiResult.relevance_quality) {
      console.log(`   ↳ relevance_quality: ${apiResult.relevance_quality}`);
    }
  } catch (e) {
    results.push({ test: "API /api/analyze call", pass: false, error: e.message });
    console.log("❌ API call failed:", e.message);
  }

  // ── Browser UI tests ─────────────────────────────────
  console.log("\n🌐 Launching browser UI tests...");
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page    = await browser.newPage();

  page.on("console", msg => {
    if (msg.type() === "error") console.log("  [BROWSER ERROR]", msg.text());
  });
  page.on("pageerror", err => console.log("  [PAGE ERROR]", err.message));

  try {
    // Test 1: Landing page loads
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    const title = await page.title();
    const hasTextarea = await page.locator("textarea").count() > 0;
    results.push({ test: "UI: page loads without crash",   pass: title.length > 0 });
    results.push({ test: "UI: textarea input is present",  pass: hasTextarea });
    console.log(title.length > 0 ? `✅ Page loaded: "${title}"` : "❌ Page failed to load");
    console.log(hasTextarea ? "✅ Textarea found" : "❌ No textarea found");
    await page.screenshot({ path: "e2e-01-landing.png", fullPage: true });

    // Test 2: Submit form
    await page.locator("textarea").fill(
      "I want to create a web series that is a satirical parody of the Bollywood movie Sholay, using the main characters but with altered motives and setting."
    );
    await sleep(500);
    await page.screenshot({ path: "e2e-02-filled.png", fullPage: true });

    // Click the submit button (look for button with CHECK CONFLICTS or similar text)
    const btn = page.locator("button").filter({ hasText: /check|conflicts|submit|analyze/i }).first();
    const btnExists = await btn.count() > 0;
    results.push({ test: "UI: submit button present", pass: btnExists });
    console.log(btnExists ? "✅ Submit button found" : "❌ Submit button not found");

    if (btnExists) {
      await btn.click();
      console.log("   ↳ Form submitted, waiting for results...");
      await page.screenshot({ path: "e2e-03-loading.png", fullPage: true });

      // Test 3: Wait for results
      try {
        // Wait for any heading that signals the report appeared
        await page.waitForSelector(
          "h2, [class*='result'], [class*='report'], [class*='analysis']",
          { timeout: TIMEOUT }
        );
        // More specific: wait for Risk Assessment section
        await page.waitForFunction(
          () => document.body.innerText.toLowerCase().includes("risk assessment") ||
                document.body.innerText.toLowerCase().includes("detailed analysis"),
          { timeout: TIMEOUT }
        );
        await sleep(1000);
        await page.screenshot({ path: "e2e-04-results.png", fullPage: true });
        results.push({ test: "UI: analysis result rendered", pass: true });
        console.log("✅ Analysis result rendered");

        // Test 4: Check for citation confidence badge
        const bodyText = await page.locator("body").innerText();
        const hasBadge = bodyText.toLowerCase().includes("citation confidence");
        results.push({ test: "UI: citation confidence badge visible", pass: hasBadge });
        console.log(hasBadge ? "✅ Citation Confidence badge visible" : "❌ Citation Confidence badge not found");

        // Test 5: Scroll to full page
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await sleep(500);
        await page.screenshot({ path: "e2e-05-full-results.png", fullPage: true });

      } catch (e) {
        results.push({ test: "UI: analysis result rendered", pass: false, error: e.message });
        console.log("❌ Result did not render:", e.message);
        await page.screenshot({ path: "e2e-04-timeout.png", fullPage: true });
      }
    }

  } catch (e) {
    console.log("❌ Browser test crashed:", e.message);
    results.push({ test: "UI: browser test run", pass: false, error: e.message });
    await page.screenshot({ path: "e2e-error.png" }).catch(() => {});
  } finally {
    await browser.close();
  }

  // ── Summary ──────────────────────────────────────────
  console.log("\n" + "=".repeat(50));
  console.log("📊 FINAL RESULTS");
  console.log("=".repeat(50));
  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;
  results.forEach(r => {
    const icon = r.pass ? "✅" : "❌";
    const err  = r.error ? `  [${r.error}]` : "";
    console.log(`  ${icon} ${r.test}${err}`);
  });
  console.log(`\n${passed} passed, ${failed} failed out of ${results.length} tests`);
  if (failed > 0) process.exit(1);
}

runTests().catch(e => {
  console.error("Fatal:", e);
  process.exit(1);
});
