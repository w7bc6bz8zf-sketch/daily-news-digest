import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            Form {
                Section("Лента") {
                    Toggle("Только русскоязычные сюжеты", isOn: $state.russianOnly)
                    NavigationLink {
                        SourcesView()
                    } label: {
                        HStack {
                            Text("Источники")
                            Spacer()
                            if !state.hiddenSources.isEmpty {
                                Text("скрыто: \(state.hiddenSources.count)")
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                Section {
                    TextField("URL ленты", text: $state.feedURL)
                        .font(.caption)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    Button("Сбросить URL по умолчанию") {
                        state.feedURL = NewsService.defaultFeedURL
                    }
                } header: {
                    Text("Данные")
                } footer: {
                    Text("Лента собирается автоматически дважды в день из 80+ изданий: русскоязычные источники в приоритете, каждый сюжет — с перспективами нескольких изданий.")
                }

                Section("О приложении") {
                    LabeledContent("Призма", value: "1.0")
                    LabeledContent("Сюжетов в ленте", value: "\(state.stories.count)")
                    if let date = state.collectedAt {
                        LabeledContent("Обновлено", value: DateParser.relative(date))
                    }
                }

                Section {
                    Button("Отметить всё прочитанным") {
                        state.readIDs.formUnion(state.stories.map(\.id))
                    }
                    Button("Сбросить прочитанное", role: .destructive) {
                        state.readIDs.removeAll()
                    }
                }
            }
            .navigationTitle("Настройки")
        }
    }
}

private struct SourcesView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        List {
            Section {
                ForEach(state.allSources, id: \.self) { source in
                    Toggle(source, isOn: Binding(
                        get: { !state.hiddenSources.contains(source) },
                        set: { enabled in
                            if enabled { state.hiddenSources.remove(source) }
                            else { state.hiddenSources.insert(source) }
                        }
                    ))
                }
            } footer: {
                Text("Выключенный источник не показывается в ленте. Сюжет скрывается, только если выключены все его источники.")
            }
        }
        .navigationTitle("Источники")
    }
}
