import Foundation

/// Placeholder ad layer so the game builds with zero external dependencies.
///
/// The hooks are already called from the right places:
///  - `showInterstitial()` fires after every 3rd game over (skipped once
///    the player buys Remove Ads).
///  - `showRewarded(completion:)` gates the one-per-run "Continue" button.
///
/// See docs/MONETIZATION.md for step-by-step Google AdMob integration.
/// Until an ad SDK is wired in, interstitials are a no-op and rewarded
/// ads grant the reward immediately.
final class AdManager {
    static let shared = AdManager()

    var adsRemoved = UserDefaults.standard.bool(forKey: "adsRemoved")

    private init() {}

    func showInterstitial() {
        guard !adsRemoved else { return }
        // TODO: present a GADInterstitialAd here once AdMob is integrated.
    }

    func showRewarded(completion: @escaping (Bool) -> Void) {
        // TODO: present a GADRewardedAd and call completion(true) only from
        // the ad's reward handler once AdMob is integrated.
        DispatchQueue.main.async { completion(true) }
    }
}
