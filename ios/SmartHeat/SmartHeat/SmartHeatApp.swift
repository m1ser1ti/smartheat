import SwiftUI
import UserNotifications

@main
struct SmartHeatApp: App {
    @State private var store = DemoStore()
    private let notificationDelegate = ForegroundNotificationDelegate()

    init() {
        UNUserNotificationCenter.current().delegate = notificationDelegate
    }

    var body: some Scene {
        WindowGroup {
            ContentView(store: store)
        }
    }
}

struct ContentView: View {
    let store: DemoStore

    var body: some View {
        if let data = store.data {
            TabView {
                Tab("Room", systemImage: "house") { RoomView(data: data) }
                Tab("Forecast", systemImage: "chart.xyaxis.line") { ForecastView(data: data) }
                Tab("Savings", systemImage: "leaf") { SavingsView(data: data) }
            }
            .safeAreaInset(edge: .top) {
                if data.synthetic { SyntheticBanner() }
            }
        } else {
            ContentUnavailableView("No data",
                                   systemImage: "exclamationmark.triangle",
                                   description: Text(store.errorMessage ?? "Unknown error"))
        }
    }
}

/// Banner so synthetic data can never be mistaken for real results in a recording.
struct SyntheticBanner: View {
    var body: some View {
        Text("Synthetic data, not real results")
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 4)
            .background(.orange.opacity(0.2), in: Capsule())
            .foregroundStyle(.orange)
    }
}

extension Double {
    var celsius: String { formatted(.number.precision(.fractionLength(1))) + " °C" }
}
