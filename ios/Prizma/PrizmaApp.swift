import SwiftUI

@main
struct PrizmaApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .task { await appState.loadInitial() }
        }
    }
}
