/**
 * Browser smoke test: loads every page in a real browser, captures console
 * errors and page errors, and exercises the create-trip flow end to end
 * against the running Flask backend.
 */
import puppeteer from 'puppeteer-core'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE = 'http://localhost:5173'

const results = []
let failures = 0

function record(name, ok, detail = '') {
  results.push({ name, ok, detail })
  if (!ok) failures += 1
  const mark = ok ? 'PASS' : 'FAIL'
  console.log(`[${mark}] ${name}${detail ? ` - ${detail}` : ''}`)
}

const browser = await puppeteer.launch({
  executablePath: EDGE,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})

const page = await browser.newPage()
await page.setViewport({ width: 1440, height: 1000 })

const consoleErrors = []
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})
page.on('pageerror', (err) => consoleErrors.push(`PAGEERROR: ${err.message}`))
page.on('requestfailed', (req) => {
  const url = req.url()
  if (url.includes('localhost:5173')) {
    consoleErrors.push(`REQFAIL: ${url} ${req.failure()?.errorText}`)
  }
})

// ---------------------------------------------------------------------------
// 1. Home page
// ---------------------------------------------------------------------------
await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 45000 })
await page.waitForSelector('#root > *', { timeout: 15000 })

const homeInfo = await page.evaluate(() => ({
  rootChildren: document.getElementById('root').children.length,
  h1: document.querySelector('h1')?.innerText?.trim() ?? '',
  navLinks: document.querySelectorAll('.navbar__link').length,
  features: document.querySelectorAll('.feature').length,
  destinations: document.querySelectorAll('.destination').length,
  steps: document.querySelectorAll('.step').length,
  footerLinks: document.querySelectorAll('.footer__column').length,
  ctaButtons: document.querySelectorAll('.hero__actions .btn').length,
}))
record('Home renders without blank screen', homeInfo.rootChildren > 0, `root children=${homeInfo.rootChildren}`)
record('Home has h1 headline', homeInfo.h1.length > 0, homeInfo.h1)
record('Home nav has links', homeInfo.navLinks >= 3, `${homeInfo.navLinks} links`)
record('Home features section', homeInfo.features === 4, `${homeInfo.features} features`)
record('Home popular destinations', homeInfo.destinations === 3, `${homeInfo.destinations} destinations`)
record('Home how-it-works steps', homeInfo.steps === 3, `${homeInfo.steps} steps`)
record('Home footer columns', homeInfo.footerLinks === 3, `${homeInfo.footerLinks} columns`)
record('Home CTA buttons present', homeInfo.ctaButtons >= 2, `${homeInfo.ctaButtons} buttons`)

// ---------------------------------------------------------------------------
// 2. Create Trip page + validation
// ---------------------------------------------------------------------------
await page.click('.navbar__cta')
await page.waitForSelector('.trip-form', { timeout: 15000 })
await new Promise((r) => setTimeout(r, 400))

const formInfo = await page.evaluate(() => ({
  url: location.pathname,
  fields: document.querySelectorAll('.form-field input, .form-field select, .form-field textarea').length,
  chips: document.querySelectorAll('.chip').length,
  submit: document.querySelector('button[type="submit"]')?.innerText?.trim() ?? '',
}))
record('Create Trip route loads', formInfo.url === '/create', formInfo.url)
record('Form has all fields', formInfo.fields >= 8, `${formInfo.fields} fields`)
record('Interest chips render', formInfo.chips >= 15, `${formInfo.chips} chips`)
record('Submit button labelled', formInfo.submit.includes('Generate'), formInfo.submit)

// Submit empty -> destination error must appear beside the field.
await page.click('button[type="submit"]')
await new Promise((r) => setTimeout(r, 500))

const validation = await page.evaluate(() => ({
  errors: [...document.querySelectorAll('.form-error')].map((e) => e.innerText.trim()),
  destinationError: document.querySelector('#error-destination')?.innerText?.trim() ?? '',
  stillOnCreate: location.pathname === '/create',
}))
record('Empty submit shows inline validation', validation.errors.length > 0, `${validation.errors.length} errors`)
record('Destination error shown beside field', validation.destinationError.length > 0, validation.destinationError)
record('Invalid submit does not navigate', validation.stillOnCreate)

// Invalid budget + invalid traveler count.
await page.type('#field-destination', 'Lisbon, Portugal')
await page.click('#field-budget', { clickCount: 3 })
await page.type('#field-budget', '-5')
await page.click('#field-travelers', { clickCount: 3 })
await page.type('#field-travelers', '0')
await page.click('button[type="submit"]')
await new Promise((r) => setTimeout(r, 500))

const numericErrors = await page.evaluate(() => ({
  budget: document.querySelector('#error-budget')?.innerText?.trim() ?? '',
  travelers: document.querySelector('#error-travelers')?.innerText?.trim() ?? '',
}))
record('Negative budget rejected', numericErrors.budget.length > 0, numericErrors.budget)
record('Zero travelers rejected', numericErrors.travelers.length > 0, numericErrors.travelers)

// Past start date rejected.
await page.evaluate(() => {
  const input = document.querySelector('#field-start_date')
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(input, '2000-01-01')
  input.dispatchEvent(new Event('input', { bubbles: true }))
})
await new Promise((r) => setTimeout(r, 300))
await page.click('button[type="submit"]')
await new Promise((r) => setTimeout(r, 500))
const pastError = await page.evaluate(() => document.querySelector('#error-start_date')?.innerText?.trim() ?? '')
record('Past start date rejected', pastError.length > 0, pastError)

// ---------------------------------------------------------------------------
// 3. Valid submit -> generates itinerary
// ---------------------------------------------------------------------------
await page.evaluate(() => {
  const set = (sel, val) => {
    const input = document.querySelector(sel)
    const proto = input.tagName === 'SELECT' ? window.HTMLSelectElement : window.HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(proto.prototype, 'value').set
    setter.call(input, val)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  }
  set('#field-start_date', '2027-04-10')
  set('#field-end_date', '2027-04-12')
  set('#field-budget', '900')
  set('#field-travelers', '2')
  set('#field-currency', 'EUR')
  set('#field-travel_style', 'balanced')
  set('#field-accommodation', 'mid-range')
  set('#field-transportation', 'mixed')
})
await new Promise((r) => setTimeout(r, 300))

// Select two interests. NOTE: the chip label is CSS-capitalised, so
// innerText returns "Food" / "Sightseeing", not the raw slug.
await page.evaluate(() => {
  const chips = [...document.querySelectorAll('.chip')]
  chips.find((c) => c.innerText.trim() === 'Food')?.click()
  chips.find((c) => c.innerText.trim() === 'Sightseeing')?.click()
})
await new Promise((r) => setTimeout(r, 600))

const selectedChips = await page.evaluate(() => ({
  count: document.querySelectorAll('.chip--active').length,
  names: [...document.querySelectorAll('.chip--active')].map((c) => c.innerText.trim()),
}))
record(
  'Interest chips toggle active (2 clicks in one batch)',
  selectedChips.count === 2 && selectedChips.names.includes('Food') && selectedChips.names.includes('Sightseeing'),
  `${selectedChips.count} selected: ${selectedChips.names.join(', ')}`,
)

const [genResponse] = await Promise.all([
  page.waitForResponse((r) => r.url().includes('/api/generate-itinerary'), { timeout: 60000 }),
  page.click('button[type="submit"]'),
])
record('Form calls /api/generate-itinerary', genResponse.url().includes('/api/generate-itinerary'), genResponse.url())
record('Generate request returns 200', genResponse.status() === 200, `HTTP ${genResponse.status()}`)

// The button must show a loading state while the request runs.
await page.waitForSelector('.itinerary-header', { timeout: 60000 })
await new Promise((r) => setTimeout(r, 600))

const itinInfo = await page.evaluate(() => ({
  url: location.pathname,
  title: document.querySelector('.itinerary-header__title')?.innerText?.trim() ?? '',
  overviewItems: document.querySelectorAll('.overview-item').length,
  days: document.querySelectorAll('.day').length,
  activities: document.querySelectorAll('.activity').length,
  budgetRows: document.querySelectorAll('.budget__row').length,
  budgetTotals: document.querySelectorAll('.budget__total').length,
  meals: document.querySelectorAll('.meals__list li').length,
  actionButtons: document.querySelectorAll('.itinerary-actions .btn').length,
  disclaimer: document.querySelector('.disclaimer p')?.innerText?.trim() ?? '',
}))
record('Itinerary page renders', itinInfo.url.startsWith('/itinerary'), itinInfo.url)
record('Trip overview shows 4 items', itinInfo.overviewItems === 4, `${itinInfo.overviewItems} items`)
record('Day sections render', itinInfo.days === 3, `${itinInfo.days} days`)
record('Activity cards render', itinInfo.activities > 5, `${itinInfo.activities} activities`)
record('Budget breakdown renders', itinInfo.budgetRows >= 3, `${itinInfo.budgetRows} rows`)
record('Budget totals render', itinInfo.budgetTotals === 4, `${itinInfo.budgetTotals} totals`)
record('Meal suggestions render', itinInfo.meals >= 3, `${itinInfo.meals} meals`)
record('Action buttons present', itinInfo.actionButtons >= 5, `${itinInfo.actionButtons} buttons`)
record('Estimate disclaimer shown', itinInfo.disclaimer.length > 10, itinInfo.disclaimer.slice(0, 60))

// ---------------------------------------------------------------------------
// 4. Save the trip
// ---------------------------------------------------------------------------
const [saveResponse] = await Promise.all([
  page.waitForResponse((r) => r.url().includes('/api/trips') && r.request().method() === 'POST', { timeout: 30000 }),
  page.evaluate(() => {
    const btn = [...document.querySelectorAll('.itinerary-actions .btn')].find((b) =>
      b.innerText.includes('Save trip'),
    )
    btn?.click()
  }),
])
record('Save trip returns 201', saveResponse.status() === 201, `HTTP ${saveResponse.status()}`)
await new Promise((r) => setTimeout(r, 1200))

const savedUrl = await page.evaluate(() => location.pathname)
record('Saved trip navigates to its own URL', savedUrl !== '/itinerary/new', savedUrl)

// ---------------------------------------------------------------------------
// 5. My Trips page
// ---------------------------------------------------------------------------
await page.goto(`${BASE}/trips`, { waitUntil: 'networkidle2', timeout: 30000 })
await new Promise((r) => setTimeout(r, 900))

const tripsInfo = await page.evaluate(() => ({
  url: location.pathname,
  cards: document.querySelectorAll('.trip-card').length,
  empty: document.querySelectorAll('.empty-state').length,
  firstTitle: document.querySelector('.trip-card__title')?.innerText?.trim() ?? '',
  badges: document.querySelectorAll('.badge').length,
  actions: document.querySelectorAll('.trip-card__actions .btn').length,
}))
record('My Trips route loads', tripsInfo.url === '/trips', tripsInfo.url)
record('Saved trip appears as card', tripsInfo.cards >= 1, `${tripsInfo.cards} cards`)
record('Trip card shows title', tripsInfo.firstTitle.length > 0, tripsInfo.firstTitle)
record('Trip card shows status badge', tripsInfo.badges >= 1, `${tripsInfo.badges} badges`)
record('Trip card has 4 actions', tripsInfo.actions >= 4, `${tripsInfo.actions} actions`)

// ---------------------------------------------------------------------------
// 6. Delete confirmation modal
// ---------------------------------------------------------------------------
await page.evaluate(() => {
  const btn = [...document.querySelectorAll('.trip-card__actions .btn')].find((b) =>
    b.innerText.includes('Delete'),
  )
  btn?.click()
})
await new Promise((r) => setTimeout(r, 500))
const modal = await page.evaluate(() => ({
  open: document.querySelectorAll('.modal').length === 1,
  title: document.querySelector('.modal__title')?.innerText?.trim() ?? '',
  hasConfirm: [...document.querySelectorAll('.modal .btn')].some((b) =>
    b.innerText.includes('Delete trip'),
  ),
  hasCancel: [...document.querySelectorAll('.modal .btn')].some((b) =>
    b.innerText.includes('Cancel'),
  ),
}))
record('Delete asks for confirmation', modal.open, modal.title)
record('Modal has confirm + cancel', modal.hasConfirm && modal.hasCancel)

// Cancel -> modal closes, trip still there.
await page.evaluate(() => {
  const btn = [...document.querySelectorAll('.modal .btn')].find((b) => b.innerText.includes('Cancel'))
  btn?.click()
})
await new Promise((r) => setTimeout(r, 400))
const afterCancel = await page.evaluate(() => document.querySelectorAll('.trip-card').length)
record('Cancel keeps the trip', afterCancel === tripsInfo.cards, `${afterCancel} cards`)

// ---------------------------------------------------------------------------
// 7. Responsive layouts
// ---------------------------------------------------------------------------
for (const [label, width, height] of [
  ['mobile', 390, 844],
  ['tablet', 768, 1024],
  ['desktop', 1440, 1000],
]) {
  await page.setViewport({ width, height })
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle2', timeout: 30000 })
  await new Promise((r) => setTimeout(r, 700))
  const overflow = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    navToggleVisible: getComputedStyle(document.querySelector('.navbar__toggle')).display !== 'none',
    bodyOverflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  }))
  record(
    `No horizontal scroll at ${label} (${width}px)`,
    !overflow.bodyOverflowX,
    `scrollW=${overflow.scrollW} clientW=${overflow.clientW}`,
  )
  if (label === 'mobile') {
    record('Mobile shows hamburger toggle', overflow.navToggleVisible)
  }
}

// ---------------------------------------------------------------------------
// 8. Console errors
// ---------------------------------------------------------------------------
const realErrors = consoleErrors.filter(
  (e) => !e.includes('favicon') && !e.includes('Download the React DevTools'),
)
record('No console errors across all pages', realErrors.length === 0, realErrors.slice(0, 3).join(' | '))

await browser.close()

console.log('\n' + '='.repeat(60))
console.log(`TOTAL: ${results.length} checks, ${results.length - failures} passed, ${failures} failed`)
console.log('='.repeat(60))
process.exit(failures > 0 ? 1 : 0)
