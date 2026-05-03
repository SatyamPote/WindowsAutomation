import SwiftUI

// Minimal theme — only font helpers.
// All colors come from system semantic values so light/dark adapts automatically.
enum Theme {
    static func mono(_ size: CGFloat) -> Font {
        .system(size: size, design: .monospaced)
    }
    static func display(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .default)
    }
    static func body(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight)
    }
}
