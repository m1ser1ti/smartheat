import Foundation

// Format is described in docs/demo_json.md. JSON keys are snake_case.

struct DemoData: Codable {
    let schemaVersion: Int
    let generatedAt: String
    let synthetic: Bool
    let notes: [String]
    let room: Room
    let forecast: Forecast
    let alert: OverheatAlert
    let advice: [Advice]
    let savings: [CitySavings]
    let assumptions: [String]

    static let supportedSchema = 1

    static func decode(_ data: Data) throws -> DemoData {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let demo = try decoder.decode(DemoData.self, from: data)
        guard demo.schemaVersion == supportedSchema else {
            throw DecodingError.dataCorrupted(.init(codingPath: [],
                debugDescription: "schema_version \(demo.schemaVersion), app expects \(supportedSchema)"))
        }
        return demo
    }
}

struct Room: Codable {
    let name: String
    let city: String
    let tempNow: Double
    let tempOutside: Double
    let targetMin: Double
    let targetMax: Double
    let overheatThreshold: Double
    let windowOpen: Bool
    let valve: Double
}

struct Forecast: Codable {
    let model: String
    let stepMinutes: Int
    // Do not name the keys "mae_1h_c": convertFromSnakeCase turns "1h" into "1H" and the field silently stays nil.
    let maeHour1C: Double?
    let maeHour3C: Double?
    let points: [ForecastPoint]
}

struct ForecastPoint: Codable, Identifiable {
    let minutes: Int
    let temp: Double
    let tempWithSystem: Double
    var id: Int { minutes }
}

struct OverheatAlert: Codable {
    let overheatInMinutes: Int?
    let title: String
    let body: String?
}

struct Advice: Codable, Identifiable {
    let id: String
    let severity: String
    let title: String
    let text: String
    var isWarning: Bool { severity == "warning" }
}

struct Range3: Codable {
    let low: Double
    let base: Double
    let high: Double
}

struct Money: Codable {
    let currency: String
    let low: Double
    let base: Double
    let high: Double
}

struct HoursAbove: Codable {
    let baseline: Double
    let smart: Double
}

struct CitySavings: Codable, Identifiable {
    let city: String
    let periodDays: Int
    let scope: String
    let buildingRooms: Int
    let kwh: Range3
    let percent: Range3
    let money: Money?
    let co2Kg: Range3?
    let hoursAbove24: HoursAbove
    var id: String { city }
}

enum RoomStatus {
    case comfortable, warm, overheating, cool

    init(temp: Double, room: Room) {
        if temp > room.overheatThreshold { self = .overheating }
        else if temp > room.targetMax { self = .warm }
        else if temp < room.targetMin { self = .cool }
        else { self = .comfortable }
    }

    var label: String {
        switch self {
        case .comfortable: "Comfortable"
        case .warm: "Warm"
        case .overheating: "Overheating"
        case .cool: "Cool"
        }
    }
}
