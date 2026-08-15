import AVFoundation
import Foundation

/// Аудио-брифинг: системный синтез речи читает топ сюжетов ленты.
/// Работает офлайн, русский и английский голоса выбираются по языку сюжета.
final class BriefingPlayer: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    @Published private(set) var isPlaying = false
    @Published private(set) var currentIndex = 0

    private let synthesizer = AVSpeechSynthesizer()
    private var queueCount = 0

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func toggle(stories: [Story]) {
        if isPlaying { stop() } else { play(stories) }
    }

    func play(_ stories: [Story]) {
        let top = Array(stories.prefix(10))
        guard !top.isEmpty else { return }
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        try? AVAudioSession.sharedInstance().setActive(true)

        queueCount = 0
        let intro = AVSpeechUtterance(string: "Аудио-брифинг Призмы. \(sourcesCountText(top.count).replacingOccurrences(of: "источник", with: "сюжет")).")
        intro.voice = AVSpeechSynthesisVoice(language: "ru-RU")
        intro.postUtteranceDelay = 0.5
        synthesizer.speak(intro)

        for (i, story) in top.enumerated() {
            let sentence = firstSentence(of: story.leadExcerpt)
            let text = story.lang == "ru"
                ? "Сюжет \(i + 1). \(story.headline). \(sentence)"
                : "\(story.headline). \(sentence)"
            let utterance = AVSpeechUtterance(string: text)
            utterance.voice = AVSpeechSynthesisVoice(language: story.lang == "ru" ? "ru-RU" : "en-US")
            utterance.rate = AVSpeechUtteranceDefaultSpeechRate
            utterance.postUtteranceDelay = 0.6
            synthesizer.speak(utterance)
            queueCount += 1
        }
        isPlaying = true
        currentIndex = 0
    }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        isPlaying = false
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    private func firstSentence(of text: String) -> String {
        guard !text.isEmpty else { return "" }
        if let dot = text.firstIndex(of: ".") {
            return String(text[...dot])
        }
        return String(text.prefix(160))
    }

    // MARK: - AVSpeechSynthesizerDelegate

    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                           didFinish utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.currentIndex += 1
            if !synthesizer.isSpeaking {
                self.isPlaying = false
                try? AVAudioSession.sharedInstance().setActive(false)
            }
        }
    }

    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                           didCancel utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            if !synthesizer.isSpeaking { self.isPlaying = false }
        }
    }
}
