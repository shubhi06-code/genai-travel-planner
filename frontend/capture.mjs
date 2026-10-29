import puppeteer from 'puppeteer-core'
import { mkdirSync } from 'node:fs'

const OUT = 'C:\\Users\\Dell\\travel_planner\\docs\\screenshots'
mkdirSync(OUT, { recursive: true })

const browser = await puppeteer.launch({
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless: 'new',
  args: ['--no-sandbox'],
})
const page = await browser.newPage()

const shots = [
  { name: '01-home', url: 'http://localhost:5173/', w: 1440, h: 1000, full: true },
  { name: '02-create-trip', url: 'http://localhost:5173/create', w: 1440, h: 1100, full: true },
  { name: '03-my-trips', url: 'http://localhost:5173/trips', w: 1440, h: 900, full: true },
]

for (const shot of shots) {
  await page.setViewport({ width: shot.w, height: shot.h })
  await page.goto(shot.url, { waitUntil: 'networkidle2', timeout: 40000 })
  await new Promise((r) => setTimeout(r, 1200))
  await page.screenshot({ path: `${OUT}\\${shot.name}.png`, fullPage: shot.full })
  console.log('captured', shot.name)
}

// Mobile home
await page.setViewport({ width: 390, height: 844 })
await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2' })
await new Promise((r) => setTimeout(r, 1000))
await page.screenshot({ path: `${OUT}\\04-home-mobile.png`, fullPage: false })
console.log('captured 04-home-mobile')

// Itinerary page - generate one first
await page.setViewport({ width: 1440, height: 1200 })
await page.goto('http://localhost:5173/create', { waitUntil: 'networkidle2' })
await page.waitForSelector('.chip')
await page.evaluate(() => {
  const set = (sel, val) => {
    const el = document.querySelector(sel)
    const proto = el.tagName === 'SELECT' ? window.HTMLSelectElement : window.HTMLInputElement
    Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, val)
    el.dispatchEvent(new Event('input', { bubbles: true }))
    el.dispatchEvent(new Event('change', { bubbles: true }))
  }
  set('#field-destination', 'Lisbon, Portugal')
  set('#field-start_date', '2027-04-10')
  set('#field-end_date', '2027-04-13')
  set('#field-budget', '1200')
  set('#field-travelers', '2')
  set('#field-currency', 'EUR')
})
await new Promise((r) => setTimeout(r, 300))
await page.evaluate(() => {
  const chips = [...document.querySelectorAll('.chip')]
  chips.find((c) => c.innerText.trim() === 'Food')?.click()
  chips.find((c) => c.innerText.trim() === 'Sightseeing')?.click()
  chips.find((c) => c.innerText.trim() === 'History')?.click()
})
await new Promise((r) => setTimeout(r, 400))
await page.click('button[type="submit"]')
await page.waitForSelector('.itinerary-header', { timeout: 60000 })
await new Promise((r) => setTimeout(r, 1200))
await page.screenshot({ path: `${OUT}\\05-itinerary.png`, fullPage: true })
console.log('captured 05-itinerary')

await browser.close()
console.log('done ->', OUT)
