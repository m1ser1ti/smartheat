import SwiftUI

struct RoomView: View {
    let data: DemoData
    @State private var notificationState: String?

    private var room: Room { data.room }
    private var status: RoomStatus { RoomStatus(temp: room.tempNow, room: room) }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(spacing: 8) {
                        Text(room.tempNow.celsius)
                            .font(.system(size: 64, weight: .semibold, design: .rounded))
                            .monospacedDigit()
                        Text(status.label)
                            .font(.headline)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(statusColor.opacity(0.15), in: Capsule())
                            .foregroundStyle(statusColor)
                        Text("Target \(Int(room.targetMin))-\(Int(room.targetMax)) °C · \(room.city)")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                }

                Section("Now") {
                    LabeledContent("Outside", value: room.tempOutside.celsius)
                    LabeledContent("Window") {
                        Label(room.windowOpen ? "Open" : "Closed",
                              systemImage: room.windowOpen ? "window.casement" : "window.casement.closed")
                    }
                    LabeledContent("Radiator valve") {
                        HStack {
                            ProgressView(value: room.valve).frame(width: 80)
                            Text(room.valve, format: .percent.precision(.fractionLength(0)))
                                .monospacedDigit()
                        }
                    }
                }

                if let minutes = data.alert.overheatInMinutes, let body = data.alert.body {
                    Section("Alert") {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Overheating in \(minutes) min", systemImage: "thermometer.sun")
                                .font(.headline)
                                .foregroundStyle(.orange)
                            Text(body).font(.subheadline)
                        }
                        Button("Send me this alert") {
                            Task {
                                let ok = await OverheatNotifier.schedule(title: data.alert.title, body: body)
                                notificationState = ok ? "Alert scheduled in 5 seconds" : "Notifications are not allowed"
                            }
                        }
                        if let notificationState {
                            Text(notificationState).font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle(room.name)
        }
    }

    private var statusColor: Color {
        switch status {
        case .comfortable: .green
        case .warm: .orange
        case .overheating: .red
        case .cool: .blue
        }
    }
}
