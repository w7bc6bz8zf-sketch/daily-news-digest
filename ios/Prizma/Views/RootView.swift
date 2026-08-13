import SwiftUI

struct RootView: View {
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
    }
}

#Preview {
    RootView().environmentObject(AppState())
}
