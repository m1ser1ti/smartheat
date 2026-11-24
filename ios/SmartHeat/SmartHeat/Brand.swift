import SwiftUI

/// Brand colors taken from the SmartHeat logo.
enum Brand {
    static let navy = Color(red: 0x14 / 255, green: 0x21 / 255, blue: 0x3D / 255)
    static let blue = Color(red: 0x1E / 255, green: 0x6F / 255, blue: 0xD9 / 255)
    static let green = Color(red: 0x18 / 255, green: 0xA8 / 255, blue: 0x74 / 255)
    static let lightGreen = Color(red: 0x3F / 255, green: 0xD6 / 255, blue: 0x9B / 255)
}

/// Small logo mark shown in the navigation bar of every screen.
struct LogoMark: View {
    var body: some View {
        Image("LogoMark")
            .resizable()
            .scaledToFit()
            .frame(width: 30, height: 30)
            .clipShape(RoundedRectangle(cornerRadius: 7, style: .continuous))
            .accessibilityLabel("SmartHeat")
    }
}
