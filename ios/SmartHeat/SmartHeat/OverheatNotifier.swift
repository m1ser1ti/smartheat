import UserNotifications

/// Local "overheating soon" notification. No server, no network.
enum OverheatNotifier {
    static let identifier = "overheat"

    /// Asks for permission and schedules the notification in `seconds` seconds (for the demo).
    static func schedule(title: String, body: String, after seconds: TimeInterval = 5) async -> Bool {
        let center = UNUserNotificationCenter.current()
        guard (try? await center.requestAuthorization(options: [.alert, .sound])) == true else { return false }

        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(1, seconds), repeats: false)
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
        do {
            try await center.add(request)
            return true
        } catch {
            return false
        }
    }
}

/// Shows the notification even while the app is open (for the screen recording).
final class ForegroundNotificationDelegate: NSObject, UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .sound]
    }
}
