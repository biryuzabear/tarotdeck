"""Everything the querent reads, in both languages.

The language setting used to reach only the cards — their names and their keywords
— while every word the interface says stayed English. It reaches all of it now.

Keys are English phrases so an untranslated string still reads as itself rather
than as a missing-key marker, and a language that lacks a key falls back to English
rather than showing a blank.
"""

ENGLISH, RUSSIAN = "en", "ru"

TABLE = {
    RUSSIAN: {
        # menus
        "TAROT": "ТАРО",
        "SETTINGS": "НАСТРОЙКИ",
        "One card": "Одна карта",
        "Two cards": "Две карты",
        "Three cards": "Три карты",
        "the day, or a plain answer": "день или простой ответ",
        "two forces pulling": "две силы тянут",
        "how it moves": "как это движется",
        # settings
        "Sound": "Звук",
        "Mode": "Режим",
        "Language": "Язык",
        "Style": "Стиль",
        "on": "включён",
        "quiet": "тихо",
        "off": "выключен",
        "english": "английский",
        "русский": "русский",
        "gravure": "гравюра",
        "the model, on the device": "модель на устройстве",
        "the model, over the network": "модель по сети",
        "no model, just the meanings": "без модели, только значения",
        # asking
        "offline": "офлайн",
        "online": "онлайн",
        "cards": "значения",
        "ask": "вопрос",
        "tap the pad and speak.": "коснитесь площадки",
        "tap again when you are done.": "и говорите.",
        "tick left to go back": "шестерёнка влево — назад",
        "listening": "слушаю",
        "tap the pad to stop": "коснитесь, чтобы остановить",
        "{seconds}s of {cap}": "{seconds}с из {cap}",
        "hearing": "разбираю",
        "putting words to it.": "подбираю слова.",
        "heard": "услышано",
        "(nothing)": "(ничего)",
        "Yes": "Да",
        "Again": "Ещё раз",
        "Back": "Назад",
        "read it": "читать",
        "say it again": "сказать заново",
        "another spread": "другой расклад",
        # reading
        "{page} of {pages}": "{page} из {pages}",
        "turn the gear": "крутите шестерёнку",
        "tick to seal": "шестерёнка вправо — закрыть",
        # trouble and rest
        "trouble": "сбой",
        "Try again": "Ещё раз",
        "Go offline": "Перейти в офлайн",
        "asleep": "спит",
        "nothing was heard": "ничего не услышано",
        "nothing was said": "ничего не сказано",
        "the network is gone": "сеть пропала",
        "the reading stopped": "чтение оборвалось",
        "something went wrong": "что-то пошло не так",
    }
}


def tr(language, text, **fmt):
    """Translate, then format. An unknown phrase comes back as itself."""
    out = TABLE.get(language, {}).get(text, text)
    return out.format(**fmt) if fmt else out


def translator(language):
    def t(text, **fmt):
        return tr(language, text, **fmt)

    return t
