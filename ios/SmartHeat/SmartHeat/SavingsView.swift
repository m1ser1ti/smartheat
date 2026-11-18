import SwiftUI

struct SavingsView: View {
    let data: DemoData
    @State private var city: String = ""

    private var selected: CitySavings? {
        data.savings.first { $0.city == city } ?? data.savings.first
    }

    var body: some View {
        NavigationStack {
            List {
                if data.savings.count > 1 {
                    Picker("City", selection: $city) {
                        ForEach(data.savings) { Text($0.city).tag($0.city) }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(Color.clear)
                }

                if let s = selected {
                    Section("Heat saved in \(s.periodDays) days") {
                        rangeRow("One room", s.kwh, unit: "kWh")
                        rangeRow("Building, \(s.buildingRooms) rooms", scaled(s.kwh, by: Double(s.buildingRooms)), unit: "kWh")
                        rangeRow("Share of heat", s.percent, unit: "%")
                    }

                    Section("Money and CO₂ (one room)") {
                        if let m = s.money {
                            rangeRow("Money", Range3(low: m.low, base: m.base, high: m.high), unit: m.currency)
                        } else {
                            LabeledContent("Money", value: "awaiting tariff")
                        }
                        if let co2 = s.co2Kg {
                            rangeRow("CO₂", co2, unit: "kg")
                        } else {
                            LabeledContent("CO₂", value: "awaiting emission factor")
                        }
                    }

                    Section("Hours above 24 °C") {
                        LabeledContent("Without system", value: hours(s.hoursAbove24.baseline))
                        LabeledContent("With SmartHeat", value: hours(s.hoursAbove24.smart))
                    }
                }

                Section("Assumptions") {
                    ForEach(data.assumptions, id: \.self) { Text($0).font(.footnote).foregroundStyle(.secondary) }
                }
            }
            .navigationTitle("Savings")
            .onAppear { if city.isEmpty { city = data.savings.first?.city ?? "" } }
        }
    }

    private func rangeRow(_ title: String, _ r: Range3, unit: String) -> some View {
        LabeledContent(title) {
            VStack(alignment: .trailing) {
                Text("\(fmt(r.base)) \(unit)").font(.headline).monospacedDigit()
                Text("range \(fmt(r.low))-\(fmt(r.high))").font(.caption).foregroundStyle(.secondary).monospacedDigit()
            }
        }
    }

    private func scaled(_ r: Range3, by k: Double) -> Range3 {
        Range3(low: r.low * k, base: r.base * k, high: r.high * k)
    }

    private func fmt(_ v: Double) -> String {
        v.formatted(.number.precision(.fractionLength(v < 100 ? 1 : 0)))
    }

    private func hours(_ h: Double) -> String {
        h.formatted(.number.precision(.fractionLength(1))) + " h"
    }
}
