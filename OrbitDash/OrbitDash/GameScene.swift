import SpriteKit
import UIKit

/// Core gameplay: the player orbits the center at constant angular speed.
/// Tapping switches between the inner and outer ring. Spikes end the run,
/// gems award soft currency. Speed ramps up over time.
final class GameScene: SKScene {
    weak var controller: GameController?

    private let player = SKShapeNode(circleOfRadius: 11)
    private let innerRing = SKShapeNode()
    private let outerRing = SKShapeNode()

    private var centerPoint: CGPoint = .zero
    private var innerRadius: CGFloat = 100
    private var outerRadius: CGFloat = 170

    private var theta: CGFloat = -.pi / 2
    private var omega: CGFloat = 1.7
    private var onOuter = true
    private var currentRadius: CGFloat = 170
    private var running = false
    private var invincibleUntil: TimeInterval = 0
    private var lastUpdate: TimeInterval = 0
    private var lastTrail: TimeInterval = 0
    private var distanceSinceSpawn: CGFloat = 0
    private var nextSpawnDistance: CGFloat = 1.0

    private final class Item {
        let node: SKShapeNode
        let angle: CGFloat
        let radius: CGFloat
        let isGem: Bool
        var passed = false

        init(node: SKShapeNode, angle: CGFloat, radius: CGFloat, isGem: Bool) {
            self.node = node
            self.angle = angle
            self.radius = radius
            self.isGem = isGem
        }
    }

    private var items: [Item] = []

    // MARK: - Setup

    override func didMove(to view: SKView) {
        backgroundColor = UIColor(red: 0.04, green: 0.05, blue: 0.12, alpha: 1)
        for ring in [innerRing, outerRing] {
            ring.strokeColor = UIColor(white: 1, alpha: 0.12)
            ring.lineWidth = 2
            ring.fillColor = .clear
            if ring.parent == nil { addChild(ring) }
        }
        player.strokeColor = UIColor(white: 1, alpha: 0.9)
        player.lineWidth = 1.5
        player.glowWidth = 4
        player.isHidden = true
        if player.parent == nil { addChild(player) }
        refreshSkin()
        addStars()
        layout()
    }

    override func didChangeSize(_ oldSize: CGSize) {
        layout()
    }

    private func layout() {
        centerPoint = CGPoint(x: size.width / 2, y: size.height / 2)
        outerRadius = min(size.width, size.height) * 0.40
        innerRadius = outerRadius * 0.60
        innerRing.path = CGPath(ellipseIn: CGRect(x: centerPoint.x - innerRadius,
                                                  y: centerPoint.y - innerRadius,
                                                  width: innerRadius * 2,
                                                  height: innerRadius * 2), transform: nil)
        outerRing.path = CGPath(ellipseIn: CGRect(x: centerPoint.x - outerRadius,
                                                  y: centerPoint.y - outerRadius,
                                                  width: outerRadius * 2,
                                                  height: outerRadius * 2), transform: nil)
    }

    private func addStars() {
        for _ in 0..<40 {
            let star = SKShapeNode(circleOfRadius: CGFloat.random(in: 0.7...1.8))
            star.fillColor = UIColor(white: 1, alpha: CGFloat.random(in: 0.15...0.5))
            star.strokeColor = .clear
            star.position = CGPoint(x: CGFloat.random(in: 0...size.width),
                                    y: CGFloat.random(in: 0...size.height))
            star.zPosition = -1
            star.run(.repeatForever(.sequence([
                .fadeAlpha(to: 0.1, duration: TimeInterval.random(in: 1...3)),
                .fadeAlpha(to: 0.6, duration: TimeInterval.random(in: 1...3)),
            ])))
            addChild(star)
        }
    }

    // MARK: - Run control

    func startGame() {
        clearItems()
        theta = -.pi / 2
        omega = 1.7
        onOuter = true
        currentRadius = outerRadius
        distanceSinceSpawn = 0
        nextSpawnDistance = 1.0
        invincibleUntil = 0
        running = true
        player.isHidden = false
        refreshSkin()
        positionPlayer()
    }

    /// Resume after a rewarded-ad continue: clear the board and grant brief invincibility.
    func continueRun() {
        clearItems()
        invincibleUntil = lastUpdate + 2.0
        running = true
        player.isHidden = false
    }

    func resetForMenu() {
        clearItems()
        running = false
        player.isHidden = true
    }

    func refreshSkin() {
        player.fillColor = controller?.playerColor ?? .cyan
    }

    private func clearItems() {
        items.forEach { $0.node.removeFromParent() }
        items.removeAll()
    }

    // MARK: - Game loop

    override func update(_ currentTime: TimeInterval) {
        defer { lastUpdate = currentTime }
        guard running else { return }
        let dt = lastUpdate == 0 ? 0 : CGFloat(min(currentTime - lastUpdate, 1.0 / 30.0))

        theta = wrap(theta + omega * dt)
        omega = min(omega + dt * 0.018, 3.4)

        let target = onOuter ? outerRadius : innerRadius
        currentRadius += (target - currentRadius) * min(1, dt * 12)
        positionPlayer()

        if currentTime - lastTrail > 0.045 {
            lastTrail = currentTime
            spawnTrailDot()
        }

        distanceSinceSpawn += omega * dt
        if distanceSinceSpawn >= nextSpawnDistance {
            distanceSinceSpawn = 0
            nextSpawnDistance = CGFloat.random(in: 0.85...1.5)
            spawnItem()
        }

        checkItems(currentTime)
    }

    private func positionPlayer() {
        player.position = point(angle: theta, radius: currentRadius)
    }

    private func point(angle: CGFloat, radius: CGFloat) -> CGPoint {
        CGPoint(x: centerPoint.x + cos(angle) * radius,
                y: centerPoint.y + sin(angle) * radius)
    }

    // MARK: - Spawning

    private func spawnItem() {
        let isGem = Int.random(in: 0..<4) == 0
        var radius = Bool.random() ? outerRadius : innerRadius
        let angle = wrap(theta + CGFloat.random(in: 2.0...2.8))

        // Fairness guard: never place a spike opposite an existing item at
        // nearly the same angle, which would wall off both rings.
        for other in items where !other.passed {
            if abs(angleDiff(angle, other.angle)) < 0.45 && abs(other.radius - radius) > 1 {
                radius = other.radius
                break
            }
        }

        let node: SKShapeNode
        if isGem {
            node = SKShapeNode(rectOf: CGSize(width: 14, height: 14), cornerRadius: 3)
            node.fillColor = UIColor(red: 0.35, green: 0.85, blue: 1.0, alpha: 1)
            node.strokeColor = .clear
            node.zRotation = .pi / 4
            node.run(.repeatForever(.sequence([
                .scale(to: 1.25, duration: 0.5),
                .scale(to: 1.0, duration: 0.5),
            ])))
        } else {
            node = spikeNode()
        }
        node.position = point(angle: angle, radius: radius)
        addChild(node)
        items.append(Item(node: node, angle: angle, radius: radius, isGem: isGem))
    }

    private func spikeNode() -> SKShapeNode {
        let path = CGMutablePath()
        path.move(to: CGPoint(x: 0, y: 12))
        path.addLine(to: CGPoint(x: -10, y: -8))
        path.addLine(to: CGPoint(x: 10, y: -8))
        path.closeSubpath()
        let node = SKShapeNode(path: path)
        node.fillColor = UIColor(red: 1.0, green: 0.3, blue: 0.4, alpha: 1)
        node.strokeColor = .clear
        return node
    }

    // MARK: - Collision & scoring

    private func checkItems(_ now: TimeInterval) {
        var survivors: [Item] = []
        for item in items {
            let diff = angleDiff(theta, item.angle)
            let sameRing = abs(currentRadius - item.radius) < 20

            if !item.passed && abs(diff) < 0.13 && sameRing {
                if item.isGem {
                    collect(item)
                    continue
                } else if now >= invincibleUntil {
                    crash()
                    return
                }
            }

            if !item.passed && diff > 0.35 {
                item.passed = true
                if !item.isGem { controller?.addPoint() }
                item.node.run(.sequence([.fadeOut(withDuration: 0.3), .removeFromParent()]))
                continue
            }

            survivors.append(item)
        }
        items = survivors
    }

    private func collect(_ item: Item) {
        controller?.collectGem()
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        let node = item.node
        node.removeAllActions()
        node.run(.sequence([
            .group([.scale(to: 1.8, duration: 0.15), .fadeOut(withDuration: 0.15)]),
            .removeFromParent(),
        ]))
    }

    private func crash() {
        running = false
        player.isHidden = true
        UINotificationFeedbackGenerator().notificationOccurred(.error)
        burst(at: player.position)
        controller?.handleGameOver()
    }

    private func burst(at position: CGPoint) {
        for _ in 0..<14 {
            let shard = SKShapeNode(circleOfRadius: 3)
            shard.fillColor = player.fillColor
            shard.strokeColor = .clear
            shard.position = position
            addChild(shard)
            let angle = CGFloat.random(in: 0...(2 * .pi))
            let distance = CGFloat.random(in: 30...90)
            shard.run(.sequence([
                .group([
                    .move(by: CGVector(dx: cos(angle) * distance, dy: sin(angle) * distance), duration: 0.5),
                    .fadeOut(withDuration: 0.5),
                ]),
                .removeFromParent(),
            ]))
        }
    }

    private func spawnTrailDot() {
        let dot = SKShapeNode(circleOfRadius: 5)
        dot.fillColor = player.fillColor.withAlphaComponent(0.4)
        dot.strokeColor = .clear
        dot.position = player.position
        dot.zPosition = -0.5
        addChild(dot)
        dot.run(.sequence([
            .group([.fadeOut(withDuration: 0.35), .scale(to: 0.2, duration: 0.35)]),
            .removeFromParent(),
        ]))
    }

    // MARK: - Input

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard running else { return }
        onOuter.toggle()
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    // MARK: - Angle helpers

    private func angleDiff(_ a: CGFloat, _ b: CGFloat) -> CGFloat {
        var d = (a - b).truncatingRemainder(dividingBy: .pi * 2)
        if d > .pi { d -= .pi * 2 }
        if d < -.pi { d += .pi * 2 }
        return d
    }

    private func wrap(_ angle: CGFloat) -> CGFloat {
        var v = angle.truncatingRemainder(dividingBy: .pi * 2)
        if v < 0 { v += .pi * 2 }
        return v
    }
}
