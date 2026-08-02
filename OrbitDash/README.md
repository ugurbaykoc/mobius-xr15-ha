# Orbit Dash 🪐

A polished one-touch arcade game for iPhone, built with SwiftUI + SpriteKit and **zero external dependencies** — it builds and runs the moment you open it in Xcode.

**Gameplay:** your ship orbits the center at ever-increasing speed. Tap anywhere to hop between the inner and outer ring. Dodge the red spikes (each one you pass = +1 score), grab the blue gems (+5 gems each), and spend gems on ship skins in the shop.

## What's built in

| Feature | Status |
|---|---|
| Core game loop (orbit, tap-to-switch, spikes, gems, speed ramp) | ✅ Complete |
| Score, best score, gem currency (persisted) | ✅ Complete |
| 6 unlockable ship skins (gem sink) | ✅ Complete |
| In-app purchases via StoreKit 2 (Remove Ads + 2 gem packs) | ✅ Complete |
| Restore purchases | ✅ Complete |
| Haptics, particle effects, star field, trail | ✅ Complete |
| Rewarded-ad "Continue" + interstitial hooks | ⚙️ Scaffolded (see `AdManager.swift` + [docs/MONETIZATION.md](docs/MONETIZATION.md)) |
| App icon (1024×1024, App Store compliant) | ✅ Complete |

## Requirements

- A Mac with **Xcode 15+**
- iOS 16.0+ device or simulator
- (For App Store release) an [Apple Developer Program](https://developer.apple.com/programs/) membership — $99/year

## Run it (2 minutes)

1. Open `OrbitDash.xcodeproj` in Xcode.
2. Select an iPhone simulator and press **⌘R**.

That's it — no packages to resolve, no signing needed for the simulator.

## Test in-app purchases locally

1. In Xcode: **Product → Scheme → Edit Scheme… → Run → Options**.
2. Set **StoreKit Configuration** to `OrbitDash.storekit`.
3. Run the app — the shop's gem packs and Remove Ads now work with sandbox purchases, no App Store Connect setup required.

## Before you ship — 3 required edits

1. **Bundle ID** — in the target's *Signing & Capabilities*, change `com.yourcompany.orbitdash` to your own reverse-domain ID and select your team.
2. **Product IDs** — update the three IDs in `StoreManager.swift` (`ProductID` enum) and `OrbitDash.storekit` to match your bundle ID; create the same three IAPs in App Store Connect.
3. **Ads (optional but recommended)** — wire up AdMob per [docs/MONETIZATION.md](docs/MONETIZATION.md). The game works and can ship without ads; IAP revenue works out of the box.

## Next steps

- 📦 [docs/APP_STORE_GUIDE.md](docs/APP_STORE_GUIDE.md) — the complete path from this repo to "Ready for Sale"
- 💰 [docs/MONETIZATION.md](docs/MONETIZATION.md) — how the money is designed to flow, AdMob integration, pricing, ASO, and realistic revenue expectations

## Project layout

```
OrbitDash/
├── OrbitDash.xcodeproj/
├── OrbitDash/
│   ├── OrbitDashApp.swift      # App entry point
│   ├── ContentView.swift       # Menu / HUD / game-over overlays
│   ├── ShopView.swift          # Skins + IAP shop
│   ├── GameScene.swift         # SpriteKit gameplay
│   ├── GameController.swift    # Shared game state & persistence
│   ├── StoreManager.swift      # StoreKit 2 purchases
│   ├── AdManager.swift         # Ad hooks (AdMob-ready)
│   ├── OrbitDash.storekit      # Local IAP testing config
│   └── Assets.xcassets/        # App icon + accent color
└── docs/
```
