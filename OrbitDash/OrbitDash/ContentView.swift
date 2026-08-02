import SwiftUI
import SpriteKit

struct ContentView: View {
    @StateObject private var game = GameController()
    @StateObject private var store = StoreManager()
    @State private var showShop = false

    var body: some View {
        ZStack {
            SpriteView(scene: game.scene)
                .ignoresSafeArea()

            switch game.phase {
            case .menu:
                menuOverlay
            case .playing:
                hud
            case .gameOver:
                gameOverOverlay
            }
        }
        .sheet(isPresented: $showShop) {
            ShopView(game: game, store: store)
        }
        .task {
            store.onGemsGranted = { [weak game] amount in
                game?.addGems(amount)
            }
            await store.start()
        }
    }

    // MARK: - Menu

    private var menuOverlay: some View {
        VStack(spacing: 22) {
            Spacer()
            Text("ORBIT DASH")
                .font(.system(size: 46, weight: .black, design: .rounded))
                .foregroundStyle(
                    LinearGradient(colors: [.cyan, .purple],
                                   startPoint: .leading, endPoint: .trailing)
                )
            Text("Tap to switch orbits.\nDodge the spikes. Grab the gems.")
                .font(.system(.body, design: .rounded))
                .multilineTextAlignment(.center)
                .foregroundColor(.white.opacity(0.7))

            HStack(spacing: 28) {
                statBadge(icon: "trophy.fill", value: "\(game.highScore)", tint: .yellow)
                statBadge(icon: "diamond.fill", value: "\(game.gems)", tint: .cyan)
            }
            .padding(.top, 4)

            Button(action: game.startGame) {
                Text("PLAY")
                    .font(.system(size: 24, weight: .heavy, design: .rounded))
                    .foregroundColor(.black)
                    .frame(width: 220, height: 60)
                    .background(Capsule().fill(Color.cyan))
            }
            .padding(.top, 12)

            Button {
                showShop = true
            } label: {
                Label("Shop", systemImage: "cart.fill")
                    .font(.system(.headline, design: .rounded))
                    .foregroundColor(.white)
                    .frame(width: 220, height: 48)
                    .background(Capsule().stroke(Color.white.opacity(0.35), lineWidth: 1.5))
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black.opacity(0.45).ignoresSafeArea())
    }

    // MARK: - In-game HUD

    private var hud: some View {
        VStack {
            HStack(alignment: .top) {
                Text("\(game.score)")
                    .font(.system(size: 56, weight: .heavy, design: .rounded))
                    .foregroundColor(.white)
                Spacer()
                statBadge(icon: "diamond.fill", value: "\(game.gems)", tint: .cyan)
            }
            .padding(.horizontal, 24)
            .padding(.top, 8)
            Spacer()
        }
        .allowsHitTesting(false)
    }

    // MARK: - Game over

    private var gameOverOverlay: some View {
        VStack(spacing: 18) {
            Spacer()
            Text("GAME OVER")
                .font(.system(size: 34, weight: .black, design: .rounded))
                .foregroundColor(.white)
            Text("\(game.score)")
                .font(.system(size: 72, weight: .heavy, design: .rounded))
                .foregroundColor(.cyan)
            Text("BEST \(game.highScore)")
                .font(.system(.headline, design: .rounded))
                .foregroundColor(.white.opacity(0.6))

            if !game.usedContinue {
                Button {
                    AdManager.shared.showRewarded { success in
                        if success { game.continueRun() }
                    }
                } label: {
                    Label("Continue (watch ad)", systemImage: "play.rectangle.fill")
                        .font(.system(.headline, design: .rounded))
                        .foregroundColor(.black)
                        .frame(width: 250, height: 52)
                        .background(Capsule().fill(Color.green))
                }
                .padding(.top, 8)
            }

            Button(action: game.startGame) {
                Text("PLAY AGAIN")
                    .font(.system(size: 20, weight: .heavy, design: .rounded))
                    .foregroundColor(.black)
                    .frame(width: 250, height: 52)
                    .background(Capsule().fill(Color.cyan))
            }

            HStack(spacing: 16) {
                Button {
                    showShop = true
                } label: {
                    Label("Shop", systemImage: "cart.fill")
                        .frame(width: 117, height: 44)
                        .background(Capsule().stroke(Color.white.opacity(0.35), lineWidth: 1.5))
                }
                Button(action: game.backToMenu) {
                    Label("Menu", systemImage: "house.fill")
                        .frame(width: 117, height: 44)
                        .background(Capsule().stroke(Color.white.opacity(0.35), lineWidth: 1.5))
                }
            }
            .font(.system(.subheadline, design: .rounded))
            .foregroundColor(.white)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black.opacity(0.55).ignoresSafeArea())
    }

    // MARK: - Shared bits

    private func statBadge(icon: String, value: String, tint: Color) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon).foregroundColor(tint)
            Text(value)
                .font(.system(.headline, design: .rounded))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(Capsule().fill(Color.white.opacity(0.1)))
    }
}
