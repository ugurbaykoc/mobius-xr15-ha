# Making money with Orbit Dash

## The honest part first

Most indie games earn very little — the median mobile game makes under $100 total. The games that earn real money share three traits: **retention** (people come back daily), **volume** (marketing/virality drives installs), and **patience** (revenue compounds over months of updates). This project gives you a correctly-built monetization machine; installs and retention are the fuel you'll need to add. Plan for: launch → measure → tune → repeat.

That said, hyper-casual arcade games are among the cheapest genres to iterate on, and everything below is wired so that every download can generate revenue from day one.

## Revenue streams (as designed in the code)

| Stream | Where it lives | Status |
|---|---|---|
| Rewarded ads — "Continue" after death | `AdManager.showRewarded`, gated one-per-run | Hook ready, needs ad SDK |
| Interstitial ads — every 3rd game over | `AdManager.showInterstitial` | Hook ready, needs ad SDK |
| **Remove Ads** — $2.99 non-consumable | `StoreManager` (StoreKit 2) | ✅ Working |
| **Gem packs** — $1.99 / $4.99 consumables | `StoreManager` + skin shop gem sink | ✅ Working |

This is the classic hyper-casual stack: ads monetize the 97% who never pay, the ads themselves sell the Remove Ads IAP, and skins give whales something to buy. Rewarded ads ("watch to continue") consistently have the highest eCPM ($10–$40 per 1000 views in the US) and players *like* them.

## Wiring up Google AdMob (~1 hour)

1. Create an [AdMob account](https://admob.google.com), register the app, create three ad units: Interstitial, Rewarded.
2. In Xcode: **File → Add Package Dependencies** → `https://github.com/googleads/swift-package-manager-google-mobile-ads`.
3. Add to the target's Info settings: `GADApplicationIdentifier` = your AdMob App ID, plus the [SKAdNetwork identifiers list](https://developers.google.com/admob/ios/quick-start#update_your_infoplist).
4. Add App Tracking Transparency: `NSUserTrackingUsageDescription` key + call `ATTrackingManager.requestTrackingAuthorization` at launch (AdMob serves non-personalized ads if declined — you still earn, just less).
5. Replace the TODO bodies in `AdManager.swift`:
   - `showInterstitial()` → load/present `GADInterstitialAd`.
   - `showRewarded(completion:)` → present `GADRewardedAd`, call `completion(true)` **only** in the reward handler (the current stub grants the continue for free — fine for testing, don't ship it that way).
6. Update the App Privacy declaration in App Store Connect (advertising data, device identifiers).

Use Google's test ad unit IDs until release day — clicking your own live ads gets your AdMob account banned.

## Pricing & tuning levers already in the code

- **Gem economy:** a gem pickup = 5 gems; skins cost 150–500. A casual player earns a skin in ~5–10 sessions — long enough that $1.99 for 500 gems is tempting. Tune costs in `GameController.skins`.
- **Interstitial cadence:** every 3rd death (`gamesSinceInterstitial >= 3`). More frequent = more revenue, worse retention. 3 is a safe start.
- **Remove Ads at $2.99:** priced so ~2–3 interstitial-annoyed sessions convert. Standard for the genre.
- **Difficulty ramp:** `omega` growth rate in `GameScene.update` (0.018/s, cap 3.4). Shorter runs = more game-overs = more ad impressions, but don't make it frustrating.

## Getting downloads (the actual hard part)

1. **ASO first** — it's free. Title + subtitle keywords ("orbit", "dash", "arcade", "one tap", "dodge"), a first screenshot that reads as fun in 0.5 seconds, and an icon that pops at 60×60px (the generated one is designed for this).
2. **Short-form video** is the #1 organic channel for hyper-casual: 15–30s clips of near-miss gameplay with a hook ("this game is ruining my life") on TikTok/YouTube Shorts/Instagram Reels. Post consistently; one modest hit = thousands of installs.
3. **Cross-promote**: Reddit (r/iosgaming playtest threads), Discord indie-game servers, Product Hunt.
4. **Later, if metrics justify it**: paid UA (Apple Search Ads starting at a few $/day) — only once you know your ARPU exceeds your cost per install.

## Realistic math

At typical hyper-casual numbers (~$0.05–$0.15 blended ARPU from ads + IAP):

| Daily downloads | Rough monthly revenue |
|---|---|
| 10/day | $15–$45 |
| 100/day | $150–$450 |
| 1,000/day | $1,500–$4,500 |

The lever is downloads, and downloads come from iteration and marketing. Ship, measure retention (D1 ≥ 25% is healthy for the genre), tune, repeat.

## Roadmap ideas that raise revenue

- **Game Center leaderboard** — free retention, and competitive players watch more continue-ads.
- **Daily reward** (gems for opening the app) — trains the daily habit.
- **"2× gems" rewarded ad** on the game-over screen — second rewarded placement, easy to add next to the existing Continue button.
- **Missions** ("collect 30 gems in one run") — session length and gem-sink pressure.
- **Seasonal skins** — scarcity sells; rotate 1–2 limited skins monthly.
