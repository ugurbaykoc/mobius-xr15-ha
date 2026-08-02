import SwiftUI
import StoreKit

struct ShopView: View {
    @ObservedObject var game: GameController
    @ObservedObject var store: StoreManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(GameController.skins) { skin in
                        skinRow(skin)
                    }
                } header: {
                    Label("Skins — \(game.gems) gems", systemImage: "diamond.fill")
                }

                Section("Gem Packs") {
                    if store.consumables.isEmpty {
                        Text("Loading products…")
                            .foregroundColor(.secondary)
                    }
                    ForEach(store.consumables, id: \.id) { product in
                        Button {
                            Task { await store.purchase(product) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(product.displayName)
                                        .foregroundColor(.primary)
                                    Text(product.description)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                Text(product.displayPrice)
                                    .fontWeight(.semibold)
                            }
                        }
                    }
                }

                Section {
                    if store.adsRemoved {
                        Label("Ads removed — thank you!", systemImage: "checkmark.seal.fill")
                            .foregroundColor(.green)
                    } else if let product = store.removeAdsProduct {
                        Button {
                            Task { await store.purchase(product) }
                        } label: {
                            HStack {
                                Text("Remove Ads")
                                    .foregroundColor(.primary)
                                Spacer()
                                Text(product.displayPrice)
                                    .fontWeight(.semibold)
                            }
                        }
                    }
                    Button("Restore Purchases") {
                        Task { await store.restore() }
                    }
                }
            }
            .navigationTitle("Shop")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private func skinRow(_ skin: Skin) -> some View {
        HStack {
            Circle()
                .fill(Color(uiColor: skin.color))
                .frame(width: 28, height: 28)
            Text(skin.name)
            Spacer()
            if game.selectedSkin == skin.id {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
            } else if game.unlockedSkins.contains(skin.id) {
                Button("Select") { game.select(skin) }
                    .buttonStyle(.borderless)
            } else {
                Button {
                    game.unlock(skin)
                } label: {
                    Label("\(skin.cost)", systemImage: "diamond.fill")
                        .font(.subheadline)
                }
                .buttonStyle(.borderedProminent)
                .tint(.cyan)
                .disabled(!game.canAfford(skin))
            }
        }
    }
}
