import Foundation
import StoreKit

/// StoreKit 2 wrapper for the game's in-app purchases.
///
/// Product IDs must match what you configure in App Store Connect
/// (and in OrbitDash.storekit for local testing). Update the prefix to
/// your own bundle identifier before shipping.
@MainActor
final class StoreManager: ObservableObject {
    enum ProductID {
        static let removeAds = "com.yourcompany.orbitdash.removeads"
        static let gems500 = "com.yourcompany.orbitdash.gems500"
        static let gems1500 = "com.yourcompany.orbitdash.gems1500"

        static let all = [removeAds, gems500, gems1500]
        static let gemAmounts: [String: Int] = [gems500: 500, gems1500: 1500]
    }

    @Published private(set) var products: [Product] = []
    @Published private(set) var adsRemoved = UserDefaults.standard.bool(forKey: "adsRemoved")

    /// Set by the owner to credit purchased gems into game state.
    var onGemsGranted: ((Int) -> Void)?

    private var updatesTask: Task<Void, Never>?

    var consumables: [Product] {
        products.filter { $0.type == .consumable }.sorted { $0.price < $1.price }
    }

    var removeAdsProduct: Product? {
        products.first { $0.id == ProductID.removeAds }
    }

    func start() async {
        updatesTask = Task { [weak self] in
            for await update in Transaction.updates {
                await self?.handle(update)
            }
        }
        await loadProducts()
        await refreshEntitlements()
    }

    deinit {
        updatesTask?.cancel()
    }

    func loadProducts() async {
        do {
            products = try await Product.products(for: ProductID.all)
        } catch {
            print("StoreManager: failed to load products: \(error)")
        }
    }

    func purchase(_ product: Product) async {
        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                await handle(verification)
            case .userCancelled, .pending:
                break
            @unknown default:
                break
            }
        } catch {
            print("StoreManager: purchase failed: \(error)")
        }
    }

    func restore() async {
        try? await AppStore.sync()
        await refreshEntitlements()
    }

    private func handle(_ verification: VerificationResult<Transaction>) async {
        guard case .verified(let transaction) = verification else { return }
        if let gems = ProductID.gemAmounts[transaction.productID], transaction.revocationDate == nil {
            onGemsGranted?(gems)
        }
        if transaction.productID == ProductID.removeAds {
            setAdsRemoved(transaction.revocationDate == nil)
        }
        await transaction.finish()
    }

    private func refreshEntitlements() async {
        var owned = false
        for await entitlement in Transaction.currentEntitlements {
            if case .verified(let transaction) = entitlement,
               transaction.productID == ProductID.removeAds,
               transaction.revocationDate == nil {
                owned = true
            }
        }
        setAdsRemoved(owned)
    }

    private func setAdsRemoved(_ value: Bool) {
        adsRemoved = value
        UserDefaults.standard.set(value, forKey: "adsRemoved")
        AdManager.shared.adsRemoved = value
    }
}
