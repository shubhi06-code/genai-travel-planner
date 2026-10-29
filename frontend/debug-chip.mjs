import puppeteer from 'puppeteer-core'

const browser = await puppeteer.launch({
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless: 'new',
  args: ['--no-sandbox'],
})
const page = await browser.newPage()
page.on('pageerror', (e) => console.log('PAGEERROR:', e.message))
page.on('console', (m) => {
  if (m.type() === 'error') console.log('CONSOLE ERROR:', m.text())
})

await page.goto('http://localhost:5173/create', { waitUntil: 'networkidle2' })
await page.waitForSelector('.chip')

console.log('--- chip count ---')
console.log(await page.evaluate(() => document.querySelectorAll('.chip').length))

console.log('--- chip texts (first 5) ---')
console.log(
  await page.evaluate(() =>
    [...document.querySelectorAll('.chip')].slice(0, 5).map((c) => JSON.stringify(c.innerText)),
  ),
)

console.log('--- click "Food" chip once (case-sensitive innerText) ---')
const afterOne = await page.evaluate(() => {
  const chip = [...document.querySelectorAll('.chip')].find(
    (c) => c.innerText.trim() === 'Food',
  )
  chip?.click()
  return { found: Boolean(chip), active: document.querySelectorAll('.chip--active').length }
})
console.log('sync:', afterOne)
await new Promise((r) => setTimeout(r, 600))
console.log(
  'after wait:',
  await page.evaluate(() => ({
    active: document.querySelectorAll('.chip--active').length,
    pressed: document.querySelectorAll('.chip[aria-pressed="true"]').length,
    names: [...document.querySelectorAll('.chip--active')].map((c) => c.innerText.trim()),
  })),
)

console.log('--- click "Sightseeing" chip (separate tick) ---')
await page.evaluate(() => {
  const chip = [...document.querySelectorAll('.chip')].find(
    (c) => c.innerText.trim() === 'Sightseeing',
  )
  chip?.click()
})
await new Promise((r) => setTimeout(r, 600))
console.log(
  'after wait:',
  await page.evaluate(() => ({
    active: document.querySelectorAll('.chip--active').length,
    names: [...document.querySelectorAll('.chip--active')].map((c) => c.innerText.trim()),
  })),
)

console.log('--- click both in the SAME tick ---')
await page.evaluate(() => {
  const chips = [...document.querySelectorAll('.chip')]
  chips.find((c) => c.innerText.trim() === 'History')?.click()
  chips.find((c) => c.innerText.trim() === 'Culture')?.click()
})
await new Promise((r) => setTimeout(r, 600))
console.log(
  'after wait:',
  await page.evaluate(() => ({
    active: document.querySelectorAll('.chip--active').length,
    names: [...document.querySelectorAll('.chip--active')].map((c) => c.innerText.trim()),
  })),
)

console.log('--- toggle OFF ---')
await page.evaluate(() => {
  const chip = [...document.querySelectorAll('.chip')].find(
    (c) => c.innerText.trim() === 'Food',
  )
  chip?.click()
})
await new Promise((r) => setTimeout(r, 600))
console.log(
  'after wait:',
  await page.evaluate(() => ({
    active: document.querySelectorAll('.chip--active').length,
    names: [...document.querySelectorAll('.chip--active')].map((c) => c.innerText.trim()),
  })),
)

await browser.close()
