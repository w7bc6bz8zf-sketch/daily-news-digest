import Foundation
import UserNotifications

/// Локальное ежедневное напоминание о свежем дайджесте.
/// Серверных push нет (приложение без бэкенда), поэтому используем
/// UNCalendarNotificationTrigger — срабатывает в выбранное время каждый день.
enum NotificationManager {
    private static let identifier = "prizma.daily.digest"

    static func applyDailyReminder(enabled: Bool, time: Date) async -> Bool {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
        guard enabled else { return true }

        let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        guard granted else { return false }

        let content = UNMutableNotificationContent()
        content.title = "Призма"
        content.body = "Свежие сюжеты собраны — загляните в ленту"
        content.sound = .default

        var components = Calendar.current.dateComponents([.hour, .minute], from: time)
        components.second = 0
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
        try? await center.add(request)
        return true
    }
}
