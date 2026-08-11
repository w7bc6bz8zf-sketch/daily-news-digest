import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var state: AppState
    @State private var notifyDenied = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Лента") {
                    Toggle("Только русскоязычные сюжеты", isOn: $state.russianOnly)
                    NavigationLink {
                        TopicsView()
                    } label: {
                        HStack {
                            Text("Мои темы")
                            Spacer()
                            if !state.followedTopics.isEmpty {
                                Text("\(state.followedTopics.count)")
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
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
                    Toggle("Ежедневное напоминание", isOn: $state.notifyEnabled)
                    if state.notifyEnabled {
                        DatePicker("Время", selection: $state.notifyTime,
                                   displayedComponents: .hourAndMinute)
                    }
                } header: {
                    Text("Уведомления")
                } footer: {
                    if notifyDenied {
                        Text("Уведомления запрещены. Разрешите их в Настройках iOS → Призма.")
                            .foregroundStyle(.red)
                    } else {
                        Text("Локальное напоминание о свежем дайджесте — сервер не используется.")
                    }
                }
                .onChange(of: state.notifyEnabled) { applyNotifications() }
                .onChange(of: state.notifyTime) { applyNotifications() }

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
                    Button("Сбросить профиль «Для вас»", role: .destructive) {
                        state.resetProfile()
                    }
                    Button("Сбросить прочитанное", role: .destructive) {
                        state.readIDs.removeAll()
                    }
                }
            }
            .navigationTitle("Настройки")
        }
    }

    private func applyNotifications() {
        Task {
            let ok = await NotificationManager.applyDailyReminder(
                enabled: state.notifyEnabled, time: state.notifyTime)
            notifyDenied = state.notifyEnabled && !ok
            if !ok && state.notifyEnabled {
                state.notifyEnabled = false
            }
        }
    }
}

// MARK: - Темы («следить за…», как в Particle)

struct TopicsView: View {
    @EnvironmentObject private var state: AppState
    @State private var newTopic = ""

    private let suggestions = [
        "Искусственный интеллект", "Криптовалюты", "Санкции", "Ключевая ставка",
        "Недвижимость", "Футбол", "Кино", "Илон Маск", "Автопром", "Космос",
    ]

    var body: some View {
        List {
            Section {
                HStack {
                    TextField("Новая тема или ключевое слово", text: $newTopic)
                        .onSubmit(addTopic)
                    Button(action: addTopic) {
                        Image(systemName: "plus.circle.fill")
                    }
                    .disabled(newTopic.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            } footer: {
                Text("Сюжеты с этими словами поднимаются в ленте «Для вас» и помечаются оранжевой меткой.")
            }

            if !state.followedTopics.isEmpty {
                Section("Вы следите") {
                    ForEach(state.followedTopics, id: \.self) { topic in
                        Text(topic)
                    }
                    .onDelete { indexSet in
                        for idx in indexSet {
                            state.unfollowTopic(state.followedTopics[idx])
                        }
                    }
                }
            }

            Section("Популярные темы") {
                ForEach(suggestions.filter { s in
                    !state.followedTopics.contains(where: { $0.caseInsensitiveCompare(s) == .orderedSame })
                }, id: \.self) { suggestion in
                    Button {
                        state.followTopic(suggestion)
                    } label: {
                        Label(suggestion, systemImage: "plus")
                    }
                }
            }
        }
        .navigationTitle("Мои темы")
    }

    private func addTopic() {
        state.followTopic(newTopic)
        newTopic = ""
    }
}

// MARK: - Источники

struct SourcesView: View {
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
