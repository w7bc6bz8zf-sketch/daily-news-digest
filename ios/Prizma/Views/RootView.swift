import SwiftUI

struct RootView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        TabView {
            FeedView()
                .tabItem { Label("Лента", systemImage: "newspaper.fill") }
            BookmarksView()
                .tabItem { Label("Закладки", systemImage: "bookmark.fill") }
            SettingsView()
                .tabItem { Label("Настройки", systemImage: "gearshape.fill") }
        }
        .tint(Theme.accent)
        .fullScreenCover(isPresented: Binding(
            get: { !state.hasOnboarded },
            set: { presented in if !presented { state.hasOnboarded = true } }
        )) {
            OnboardingView()
        }
    }
}

#Preview {
    RootView().environmentObject(AppState())
}
