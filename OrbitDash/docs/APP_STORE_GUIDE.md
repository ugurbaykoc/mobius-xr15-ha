# From this repo to the App Store

The honest, complete checklist. Budget **1–2 evenings** of setup plus **1–3 days** of Apple review time.

## Prerequisites

| What | Cost | Why |
|---|---|---|
| A Mac with Xcode 15+ | — | Only Macs can build & upload iOS apps |
| Apple ID | Free | Sign into Xcode |
| [Apple Developer Program](https://developer.apple.com/programs/enroll/) | **$99/year** | Required to distribute on the App Store and to use in-app purchases |

Enroll as an **individual** (fastest, your legal name shows as the seller) unless you have an LLC/company. Enrollment approval usually takes 24–48h.

## Step 1 — Make the project yours (10 min)

1. Clone this repo on your Mac, open `OrbitDash/OrbitDash.xcodeproj`.
2. Target **OrbitDash → Signing & Capabilities**: select your **Team**, change the bundle ID to something you own, e.g. `com.ugurbaykoc.orbitdash`.
3. In `StoreManager.swift` and `OrbitDash.storekit`, replace the `com.yourcompany.orbitdash.*` product IDs with your bundle-ID prefix (e.g. `com.ugurbaykoc.orbitdash.removeads`).
4. Build and run on a real iPhone (free with any Apple ID) — play it, tune it, make sure you enjoy it. Reviewers and players can tell.

## Step 2 — App Store Connect setup (30 min)

1. Go to [App Store Connect](https://appstoreconnect.apple.com) → **My Apps → ＋ → New App**.
   - Platform: iOS · Name: **Orbit Dash** (or your own — names must be unique store-wide, have backups ready)
   - Bundle ID: the one from Step 1 · SKU: anything, e.g. `orbitdash001`
2. **In-App Purchases** section — create three products matching your IDs exactly:
   | Reference name | Type | Price |
   |---|---|---|
   | Remove Ads | Non-Consumable | $2.99 |
   | 500 Gems | Consumable | $1.99 |
   | 1500 Gems | Consumable | $4.99 |
   Each needs a display name, description, and a review screenshot (a screenshot of the shop screen is fine).
3. **App Privacy**: as shipped (no ads SDK, no analytics) the game collects **no data** — declare "Data Not Collected." ⚠️ If you add AdMob later, you must update this to declare tracking/advertising data and add App Tracking Transparency (see MONETIZATION.md).
4. Fill in: description, keywords, support URL (a GitHub Pages page or even this repo's URL works), marketing URL (optional), age rating questionnaire (this game is 4+).

## Step 3 — Screenshots (30 min)

Required sizes: **6.9″/6.7″ iPhone** (and 6.5″ or 5.5″ covers older devices in most cases).

Easy path: run the game in the iPhone 15 Pro Max simulator, press **⌘S** during gameplay, on the menu, and in the shop. 3–5 screenshots is plenty. Put your best gameplay shot first — it's what shows in search results.

## Step 4 — Upload the build (15 min)

1. In Xcode: select **Any iOS Device (arm64)** as the destination.
2. **Product → Archive**.
3. In the Organizer window: **Distribute App → App Store Connect → Upload**. Accept the defaults.
4. Wait ~15 min for processing, then the build appears in App Store Connect.

## Step 5 — TestFlight first (recommended)

In App Store Connect → **TestFlight**, add yourself and a few friends as internal testers. Catch crashes and confusing UX before Apple's reviewers do. Even 2–3 days of testing meaningfully improves your review odds and your ratings.

## Step 6 — Submit for review

1. On the app's **App Store** tab, select your build, attach the IAPs to this version, and **Submit for Review**.
2. Typical review time: **24–72 hours**.
3. Common rejection reasons to pre-empt:
   - **Guideline 2.1 (crashes/bugs)** — test the IAP flow and restore purchases on a real device.
   - **Guideline 3.1.1** — all IAPs must be purchasable and restorable in-app (the Restore button in the shop covers this).
   - **Guideline 4.3 (spam/minimal functionality)** — this is the big one for simple arcade games. Differentiate: tune difficulty, consider adding Game Center leaderboards, unique visuals, or extra modes before submitting.

If rejected: read the message carefully, fix, resubmit — resubmissions are usually reviewed faster. Rejection is routine, not fatal.

## Step 7 — Release

Choose **Manually release** or **Automatically release** after approval. Once live, the money mechanics in [MONETIZATION.md](MONETIZATION.md) take over.

## Ongoing

- Respond to reviews (App Store Connect → Ratings) — it visibly boosts conversion.
- Ship small updates every 2–4 weeks; update recency is an App Store ranking signal.
- Watch App Analytics (impressions → product page views → downloads funnel) to see where you're losing people.
