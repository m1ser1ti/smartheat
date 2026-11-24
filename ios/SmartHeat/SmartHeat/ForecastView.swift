import Charts
import SwiftUI

struct ForecastView: View {
    let data: DemoData

    private var room: Room { data.room }
    private var forecast: Forecast { data.forecast }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    chart
                        .frame(height: 240)
                        .padding(.vertical, 8)
                } header: {
                    Text("Next 3 hours")
                } footer: {
                    Text(modelNote)
                }

                Section("Advice") {
                    ForEach(data.advice) { advice in
                        VStack(alignment: .leading, spacing: 4) {
                            Label(advice.title, systemImage: advice.isWarning ? "exclamationmark.triangle.fill" : "lightbulb")
                                .font(.headline)
                                .foregroundStyle(advice.isWarning ? .orange : .primary)
                            Text(advice.text)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 2)
                    }
                }
            }
            .navigationTitle("Forecast")
            .toolbar { ToolbarItem(placement: .topBarTrailing) { LogoMark() } }
        }
    }

    private var chart: some View {
        Chart {
            RectangleMark(yStart: .value("Min", room.targetMin), yEnd: .value("Max", room.targetMax))
                .foregroundStyle(Brand.lightGreen.opacity(0.18))
            RuleMark(y: .value("Overheat", room.overheatThreshold))
                .foregroundStyle(.red.opacity(0.6))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                .annotation(position: .top, alignment: .leading) {
                    Text("Overheat \(Int(room.overheatThreshold)) °C").font(.caption2).foregroundStyle(.red)
                }
            ForEach(forecast.points) { p in
                LineMark(x: .value("Minutes", p.minutes), y: .value("°C", p.temp),
                         series: .value("Scenario", "No action"))
                    .foregroundStyle(by: .value("Scenario", "No action"))
                LineMark(x: .value("Minutes", p.minutes), y: .value("°C", p.tempWithSystem),
                         series: .value("Scenario", "With SmartHeat"))
                    .foregroundStyle(by: .value("Scenario", "With SmartHeat"))
            }
        }
        .chartForegroundStyleScale(["No action": Color.orange, "With SmartHeat": Brand.green])
        .chartXAxis {
            AxisMarks(values: [0, 60, 120, 180]) { value in
                AxisGridLine()
                // Edge labels are anchored inward, otherwise "+3 h" at the right edge gets dropped.
                let m = value.as(Int.self) ?? 0
                AxisValueLabel(anchor: m == 0 ? .topLeading : (m == 180 ? .topTrailing : .top),
                               collisionResolution: .disabled) {
                    Text(m == 0 ? "now" : "+\(m / 60) h")
                }
            }
        }
        .chartYScale(domain: yDomain)
        .chartLegend(position: .bottom)
    }

    private var yDomain: ClosedRange<Double> {
        let temps = forecast.points.flatMap { [$0.temp, $0.tempWithSystem] } + [room.targetMin, room.overheatThreshold]
        return (temps.min()! - 0.5)...(temps.max()! + 0.5)
    }

    private var modelNote: String {
        var note = "Source: \(forecast.model)."
        let errors = [("1 h", forecast.maeHour1C), ("3 h", forecast.maeHour3C)].compactMap { label, mae in
            mae.map { "\(label) ±\($0.formatted(.number.precision(.fractionLength(2)))) °C" }
        }
        if !errors.isEmpty {
            note += " LightGBM error on real rooms (ThermBuild test data): " + errors.joined(separator: ", ") + "."
        }
        return note
    }
}
