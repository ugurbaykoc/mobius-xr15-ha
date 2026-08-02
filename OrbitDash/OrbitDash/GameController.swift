import SwiftUI
import UIKit
import SpriteKit

enum GamePhase {
    case menu
    case playing
    case gameOver
}

struct Skin: Identifiable {
    let id: Int
    let name: String
    let color: UIColor
    let cost: Int
}

/// Central game state shared between the SwiftUI overlays and the SpriteKit scene.
final class GameController: ObservableObject {
    @Published var phase: GamePhase = .menu
    @Published var score = 0
    @Published var gems: Int
    @Published var highScore: Int
    @Published var selectedSkin: Int
    @Published var unlockedSkins: Set<Int>

    /// One rewarded-ad continue per run.
    var usedContinue = false
    private var gamesSinceInterstitial = 0

    static let skins: [Skin] = [
        Skin(id: 0, name: "Comet", color: UIColor(red: 0.22, green: 0.90, blue: 1.00, alpha: 1), cost: 0),
        Skin(id: 1, name: "Ember", color: UIColor(red: 1.00, green: 0.45, blue: 0.25, alpha: 1), cost: 150),
        Skin(id: 2, name: "Lime", color: UIColor(red: 0.55, green: 0.95, blue: 0.35, alpha: 1), cost: 150),
        Skin(id: 3, name: "Violet", color: UIColor(red: 0.70, green: 0.45, blue: 1.00, alpha: 1), cost: 300),
        Skin(id: 4, name: "Gold", color: UIColor(red: 1.00, green: 0.80, blue: 0.25, alpha: 1), cost: 500),
        Skin(id: 5, name: "Rose", color: UIColor(red: 1.00, green: 0.40, blue: 0.65, alpha: 1), cost: 500),
    ]

    private let defaults = UserDefaults.standard

    lazy var scene: GameScene = {
        let s = GameScene(size: CGSize(width: 390, height: 844))
        s.scaleMode = .resizeFill
        s.controller = self
        return s
    }()

    init() {
        gems = defaults.integer(forKey: "gems")
        highScore = defaults.integer(forKey: "highScore")
        selectedSkin = defaults.integer(forKey: "selectedSkin")
        var stored = Set((defaults.array(forKey: "unlockedSkins") as? [Int]) ?? [])
        stored.insert(0)
        unlockedSkins = stored
    }

    var playerColor: UIColor {
        Self.skins.first(where: { $0.id == selectedSkin })?.color ?? Self.skins[0].color
    }

    // MARK: - Run lifecycle

    func startGame() {
        score = 0
        usedContinue = false
        phase = .playing
        scene.startGame()
    }

    /// Called by the scene when the player crashes.
    func handleGameOver() {
        gamesSinceInterstitial += 1
        if score > highScore {
            highScore = score
            defaults.set(highScore, forKey: "highScore")
        }
        phase = .gameOver
        if gamesSinceInterstitial >= 3 {
            gamesSinceInterstitial = 0
            AdManager.shared.showInterstitial()
        }
    }

    func continueRun() {
        usedContinue = true
        phase = .playing
        scene.continueRun()
    }

    func backToMenu() {
        phase = .menu
        scene.resetForMenu()
    }

    // MARK: - Scoring & currency

    func addPoint() { score += 1 }

    func collectGem() {
        gems += 5
        persistGems()
    }

    func addGems(_ amount: Int) {
        gems += amount
        persistGems()
    }

    private func persistGems() { defaults.set(gems, forKey: "gems") }

    // MARK: - Skins

    func canAfford(_ skin: Skin) -> Bool { gems >= skin.cost }

    func unlock(_ skin: Skin) {
        guard !unlockedSkins.contains(skin.id), gems >= skin.cost else { return }
        gems -= skin.cost
        persistGems()
        unlockedSkins.insert(skin.id)
        defaults.set(Array(unlockedSkins), forKey: "unlockedSkins")
        select(skin)
    }

    func select(_ skin: Skin) {
        guard unlockedSkins.contains(skin.id) else { return }
        selectedSkin = skin.id
        defaults.set(selectedSkin, forKey: "selectedSkin")
        scene.refreshSkin()
    }
}
