import Foundation
import Observation

/// Loads demo.json from the app bundle.
@Observable
final class DemoStore {
    private(set) var data: DemoData?
    private(set) var errorMessage: String?

    init(bundle: Bundle = .main) {
        guard let url = bundle.url(forResource: "demo", withExtension: "json") else {
            errorMessage = "demo.json is missing from the app bundle"
            return
        }
        do {
            data = try DemoData.decode(Data(contentsOf: url))
        } catch {
            errorMessage = "Cannot read demo.json: \(error)"
        }
    }
}
