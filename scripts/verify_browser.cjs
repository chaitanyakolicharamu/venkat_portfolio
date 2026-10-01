// Local demo smoke test and real screenshots. Requires Playwright + Chromium.
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname,'..');
const agentUrl = process.env.AGENT_URL || 'http://127.0.0.1:8011';
const ragUrl = process.env.RAG_URL || 'http://127.0.0.1:8012';
(async()=>{
  const options = {headless:true};
  if (process.env.CHROMIUM_EXECUTABLE_PATH) {
    options.executablePath = process.env.CHROMIUM_EXECUTABLE_PATH;
    options.args = ['--disable-gpu'];
  }
  if (process.env.CHROMIUM_PACKAGE) {
    const loaded = require(process.env.CHROMIUM_PACKAGE);
    const packaged = loaded.default || loaded;
    options.executablePath = await packaged.executablePath();
    options.args = packaged.args;
  }
  const browser = await chromium.launch(options);
  const page = await browser.newPage({viewport:{width:1440,height:1120},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  for(const p of ['secure-agentic-ai','healthcare-rag-evaluation']) fs.mkdirSync(path.join(root,p,'docs'),{recursive:true});
  await page.goto(agentUrl);
  await page.waitForFunction(()=>document.querySelector('#completion').textContent.includes('/'));
  await page.locator('#run').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='completed');
  assert.match(await page.locator('#answer').innerText(),/pool saturation/);
  await page.screenshot({path:path.join(root,'secure-agentic-ai/docs/control-room.png'),fullPage:true});
  await page.locator('[data-scenario="approval"]').click();
  await page.locator('#run').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='awaiting review');
  await page.screenshot({path:path.join(root,'secure-agentic-ai/docs/human-review.png'),fullPage:true});
  await page.locator('#reject').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='rejected');
  await page.locator('#run').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='awaiting review');
  await page.locator('#approve').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='completed');
  assert.match(await page.locator('#answer').innerText(),/Created sandbox ticket/);
  await page.locator('[data-scenario="safety"]').click();
  await page.locator('#run').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='blocked');
  assert.equal(await page.locator('#trace li').count(),1);
  await page.goto(ragUrl);
  await page.waitForFunction(()=>document.querySelector('#hitRate').textContent.includes('%'));
  await page.locator('#ask').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='answered');
  assert.match(await page.locator('#answer').innerText(),/24 hours/);
  await page.screenshot({path:path.join(root,'healthcare-rag-evaluation/docs/evidence-lab.png'),fullPage:true});
  await page.locator('#tenant').selectOption('south');
  await page.locator('#ask').click();
  await page.waitForFunction(()=>document.querySelector('#answer').textContent.includes('48 hours'));
  await page.locator('[data-query="What is the capital of Mars?"]').click();
  await page.locator('#ask').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='abstained');
  await page.setViewportSize({width:390,height:844});
  for(const url of [agentUrl,ragUrl]){
    await page.goto(url);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'Mobile layout overflows');
  }
  assert.deepEqual(errors,[]);
  console.log('Browser checks passed: incident, pause/reject/approve, input block, tenant-specific citations, abstention, mobile widths; no JS errors.');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
