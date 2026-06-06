import logging
import re
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# === настройки ===
BOT_TOKEN = "ВАШ_BOT_TOKEN"
TARGET_CHAT_ID = 123456789
# ================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pending_replies = {}

OUTPUT_FIAT = ["GBP", "CHF", "EUR", "USD", "UAH", "RUB"]
OUTPUT_CRYPTO = ["BTC", "ETH"]

CURRENCY_FLAGS = {
    "UAH": "🇺🇦", "RUB": "🇷🇺", "USD": "🇺🇸", "EUR": "🇪🇺",
    "GBP": "🇬🇧", "CHF": "🇨🇭", "JPY": "🇯🇵", "CNY": "🇨🇳",
    "PLN": "🇵🇱", "TRY": "🇹🇷", "KZT": "🇰🇿", "IDR": "🇮🇩",
    "THB": "🇹🇭", "SGD": "🇸🇬", "AED": "🇦🇪", "INR": "🇮🇳",
    "UGX": "🇺🇬", "CZK": "🇨🇿", "MXN": "🇲🇽", "BRL": "🇧🇷",
    "CAD": "🇨🇦", "AUD": "🇦🇺", "NZD": "🇳🇿", "HKD": "🇭🇰",
    "NOK": "🇳🇴", "SEK": "🇸🇪", "DKK": "🇩🇰", "ZAR": "🇿🇦",
    "ILS": "🇮🇱", "SAR": "🇸🇦", "MYR": "🇲🇾", "PHP": "🇵🇭",
    "VND": "🇻🇳", "PKR": "🇵🇰", "BDT": "🇧🇩", "COP": "🇨🇴",
    "ARS": "🇦🇷", "CLP": "🇨🇱", "PEN": "🇵🇪", "RON": "🇷🇴",
    "HUF": "🇭🇺", "BGN": "🇧🇬", "HRK": "🇭🇷", "RSD": "🇷🇸",
    "UZS": "🇺🇿", "AMD": "🇦🇲", "GEL": "🇬🇪", "AZN": "🇦🇿",
    "BYN": "🇧🇾", "MDL": "🇲🇩", "KGS": "🇰🇬", "TJS": "🇹🇯",
    "TMT": "🇹🇲", "MNT": "🇲🇳", "KRW": "🇰🇷", "TWD": "🇹🇼",
    "IRR": "🇮🇷", "IQD": "🇮🇶", "EGP": "🇪🇬", "NGN": "🇳🇬",
    "KES": "🇰🇪", "GHS": "🇬🇭", "TZS": "🇹🇿", "ETB": "🇪🇹",
    "MAD": "🇲🇦", "DZD": "🇩🇿", "TND": "🇹🇳", "LYD": "🇱🇾",
    "XOF": "🌍", "XAF": "🌍", "MZN": "🇲🇿", "AOA": "🇦🇴",
    "ZMW": "🇿🇲", "BWP": "🇧🇼", "NAD": "🇳🇦", "MUR": "🇲🇺",
    "SCR": "🇸🇨", "SDG": "🇸🇩", "SOS": "🇸🇴", "LKR": "🇱🇰",
    "NPR": "🇳🇵", "MMK": "🇲🇲", "KHR": "🇰🇭", "LAK": "🇱🇦",
    "BND": "🇧🇳", "MOP": "🇲🇴", "KPW": "🇰🇵", "MVR": "🇲🇻",
    "AFN": "🇦🇫", "BHD": "🇧🇭", "JOD": "🇯🇴", "KWD": "🇰🇼",
    "LBP": "🇱🇧", "OMR": "🇴🇲", "QAR": "🇶🇦", "SYP": "🇸🇾",
    "YER": "🇾🇪", "ISK": "🇮🇸", "HNL": "🇭🇳", "GTQ": "🇬🇹",
    "CRC": "🇨🇷", "PAB": "🇵🇦", "DOP": "🇩🇴", "BOB": "🇧🇴",
    "PYG": "🇵🇾", "UYU": "🇺🇾", "VES": "🇻🇪", "CUP": "🇨🇺",
    "JMD": "🇯🇲", "TTD": "🇹🇹", "BBD": "🇧🇧", "GYD": "🇬🇾",
    "SRD": "🇸🇷", "AWG": "🇦🇼", "BSD": "🇧🇸", "BZD": "🇧🇿",
    "HTG": "🇭🇹", "NIO": "🇳🇮", "SVC": "🇸🇻", "ALL": "🇦🇱",
    "BAM": "🇧🇦", "MKD": "🇲🇰", "UAH": "🇺🇦", "BTC": "₿", "ETH": "Ξ",
}

CURRENCY_SYMBOLS = {
    "UAH": "₴", "RUB": "₽", "USD": "$", "EUR": "€",
    "GBP": "£", "CHF": "Fr", "JPY": "¥", "CNY": "¥",
    "PLN": "zł", "TRY": "₺", "KZT": "₸", "IDR": "Rp",
    "THB": "฿", "SGD": "S$", "AED": "د.إ", "INR": "₹",
    "BTC": "", "ETH": "",
}

CURRENCY_ALIASES = {
    "UAH": ["uah", "грн", "гривен", "гривна", "гривны", "гривні", "гривень", "hryvnia", "₴"],
    "RUB": ["rub", "руб", "рублей", "рубль", "рубля", "rouble", "₽"],
    "USD": ["usd", "доллар", "долларов", "доллара", "баксов", "бакс", "dollar", "dollars", "$"],
    "EUR": ["eur", "евро", "euro", "euros", "€"],
    "GBP": ["gbp", "фунт", "фунтов", "фунта", "pound", "pounds", "sterling", "£"],
    "CHF": ["chf", "франк", "франков", "франка", "franc", "francs", "swiss franc"],
    "BTC": ["btc", "биткоин", "биткоина", "биткоинов", "bitcoin", "битка", "биток", "₿"],
    "ETH": ["eth", "эфир", "эфира", "эфиров", "эфириум", "ethereum", "ether"],
    "JPY": ["jpy", "иена", "иен", "иены", "yen", "¥"],
    "CNY": ["cny", "юань", "юаня", "юаней", "yuan", "renminbi", "rmb"],
    "PLN": ["pln", "злотый", "злотых", "злотого", "zloty", "zł"],
    "TRY": ["try", "лира", "лир", "лиры", "lira", "lire", "₺"],
    "KZT": ["kzt", "тенге", "tenge", "₸"],
    "IDR": ["idr", "рупия индонезийская", "rupiah"],
    "THB": ["thb", "бат", "батов", "baht"],
    "SGD": ["sgd", "singapore dollar"],
    "AED": ["aed", "дирхам", "дирхамов", "dirham"],
    "INR": ["inr", "рупия", "рупий", "indian rupee", "rupee", "₹"],
    "UGX": ["ugx", "uganda shilling"],
    "CZK": ["czk", "крона чешская", "czech koruna", "koruna"],
    "MXN": ["mxn", "песо мексиканское", "mexican peso"],
    "BRL": ["brl", "реал", "реала", "real", "brazilian real"],
    "CAD": ["cad", "канадский доллар", "canadian dollar"],
    "AUD": ["aud", "австралийский доллар", "australian dollar"],
    "NZD": ["nzd", "новозеландский доллар", "new zealand dollar"],
    "HKD": ["hkd", "гонконгский доллар", "hong kong dollar"],
    "NOK": ["nok", "норвежская крона", "norwegian krone"],
    "SEK": ["sek", "шведская крона", "swedish krona"],
    "DKK": ["dkk", "датская крона", "danish krone"],
    "ZAR": ["zar", "рэнд", "rand"],
    "KRW": ["krw", "вона", "won", "korean won"],
    "SAR": ["sar", "риял", "riyal", "saudi riyal"],
    "KWD": ["kwd", "кувейтский динар", "kuwaiti dinar"],
    "BHD": ["bhd", "бахрейнский динар", "bahraini dinar"],
    "OMR": ["omr", "оманский риал", "omani rial"],
    "QAR": ["qar", "катарский риял", "qatari riyal"],
    "JOD": ["jod", "иорданский динар", "jordanian dinar"],
    "ILS": ["ils", "шекель", "shekel", "israeli shekel"],
    "GEL": ["gel", "лари", "lari", "georgian lari"],
    "AZN": ["azn", "манат азербайджанский", "azerbaijani manat"],
    "AMD": ["amd", "драм", "dram", "armenian dram"],
    "BYN": ["byn", "белорусский рубль", "belarusian ruble"],
    "MDL": ["mdl", "молдавский лей", "moldovan leu"],
    "KGS": ["kgs", "сом", "som", "kyrgyzstani som"],
    "UZS": ["uzs", "узбекский сум", "uzbekistani sum"],
    "TJS": ["tjs", "сомони", "somoni", "tajikistani somoni"],
    "TMT": ["tmt", "туркменский манат", "turkmenistani manat"],
}

FLAG_TO_CURRENCY = {
    "🇺🇸": "USD", "🇪🇺": "EUR", "🇬🇧": "GBP", "🇨🇭": "CHF",
    "🇷🇺": "RUB", "🇺🇦": "UAH", "🇯🇵": "JPY", "🇨🇳": "CNY",
    "🇵🇱": "PLN", "🇹🇷": "TRY", "🇰🇿": "KZT", "🇮🇩": "IDR",
    "🇹🇭": "THB", "🇸🇬": "SGD", "🇦🇪": "AED", "🇮🇳": "INR",
    "🇺🇬": "UGX", "🇨🇿": "CZK", "🇲🇽": "MXN", "🇧🇷": "BRL",
    "🇨🇦": "CAD", "🇦🇺": "AUD", "🇳🇿": "NZD", "🇭🇰": "HKD",
    "🇳🇴": "NOK", "🇸🇪": "SEK", "🇩🇰": "DKK", "🇿🇦": "ZAR",
    "🇮🇱": "ILS", "🇸🇦": "SAR", "🇲🇾": "MYR", "🇵🇭": "PHP",
    "🇻🇳": "VND", "🇵🇰": "PKR", "🇧🇩": "BDT", "🇨🇴": "COP",
    "🇦🇷": "ARS", "🇨🇱": "CLP", "🇵🇪": "PEN", "🇷🇴": "RON",
    "🇭🇺": "HUF", "🇧🇬": "BGN", "🇷🇸": "RSD", "🇺🇿": "UZS",
    "🇦🇲": "AMD", "🇬🇪": "GEL", "🇦🇿": "AZN", "🇧🇾": "BYN",
    "🇲🇩": "MDL", "🇰🇬": "KGS", "🇹🇯": "TJS", "🇹🇲": "TMT",
    "🇲🇳": "MNT", "🇰🇷": "KRW", "🇹🇼": "TWD", "🇮🇷": "IRR",
    "🇮🇶": "IQD", "🇪🇬": "EGP", "🇳🇬": "NGN", "🇰🇪": "KES",
    "🇬🇭": "GHS", "🇹🇿": "TZS", "🇪🇹": "ETB", "🇲🇦": "MAD",
    "🇩🇿": "DZD", "🇹🇳": "TND", "🇱🇾": "LYD", "🇲🇿": "MZN",
    "🇦🇴": "AOA", "🇿🇲": "ZMW", "🇧🇼": "BWP", "🇳🇦": "NAD",
    "🇱🇰": "LKR", "🇳🇵": "NPR", "🇲🇲": "MMK", "🇰🇭": "KHR",
    "🇱🇦": "LAK", "🇧🇳": "BND", "🇦🇫": "AFN", "🇧🇭": "BHD",
    "🇯🇴": "JOD", "🇰🇼": "KWD", "🇱🇧": "LBP", "🇴🇲": "OMR",
    "🇶🇦": "QAR", "🇾🇪": "YER", "🇮🇸": "ISK", "🇭🇳": "HNL",
    "🇬🇹": "GTQ", "🇨🇷": "CRC", "🇵🇦": "PAB", "🇩🇴": "DOP",
    "🇧🇴": "BOB", "🇵🇾": "PYG", "🇺🇾": "UYU", "🇨🇺": "CUP",
    "🇯🇲": "JMD", "🇹🇹": "TTD", "🇬🇾": "GYD", "🇸🇷": "SRD",
    "🇭🇹": "HTG", "🇳🇮": "NIO", "🇦🇱": "ALL", "🇧🇦": "BAM",
    "🇲🇰": "MKD", "🇮🇸": "ISK",
}


def detect_currency(text: str):
    t = text.strip()
    num_match = re.search(r'(\d+(?:[.,]\d+)?)', t)
    if not num_match:
        return None
    amount = float(num_match.group(1).replace(',', '.'))

    for flag, code in FLAG_TO_CURRENCY.items():
        if flag in t:
            return amount, code

    t_lower = t.lower()
    all_aliases = [(alias, code) for code, aliases in CURRENCY_ALIASES.items() for alias in aliases]
    all_aliases.sort(key=lambda x: -len(x[0]))

    for alias, code in all_aliases:
        escaped = re.escape(alias)
        if re.search(r'(?<![а-яёa-z])' + escaped + r'(?![а-яёa-z])', t_lower):
            return amount, code

    iso_match = re.search(r'\b([A-Z]{3})\b', t)
    if iso_match:
        return amount, iso_match.group(1)

    return None


def format_number(n: float) -> str:
    if n >= 1000:
        return f"{n:,.2f}".replace(",", " ")
    elif n >= 1:
        return f"{n:.2f}"
    elif n >= 0.01:
        return f"{n:.4f}"
    else:
        return f"{n:.8f}"


def escape_md(text: str) -> str:
    special = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in special else c for c in text)


async def get_fiat_rates(base: str, targets: list) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"https://api.exchangerate-api.com/v4/latest/{base}")
            data = r.json()
            rates = data.get("rates", {})
            return {t: rates[t] for t in targets if t in rates}
    except Exception as e:
        logger.error(f"ошибка фиат: {e}")
        return {}


async def get_crypto_in_usd() -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price"
                "?ids=bitcoin,ethereum&vs_currencies=usd"
            )
            data = r.json()
            result = {}
            btc = data.get("bitcoin", {}).get("usd")
            eth = data.get("ethereum", {}).get("usd")
            if btc:
                result["BTC"] = btc
            if eth:
                result["ETH"] = eth
            return result
    except Exception as e:
        logger.error(f"ошибка крипто: {e}")
        return {}


async def convert_all(amount: float, from_currency: str) -> dict:
    result = {}

    if from_currency in ("BTC", "ETH"):
        crypto_usd = await get_crypto_in_usd()
        price_usd = crypto_usd.get(from_currency)
        if not price_usd:
            return {}
        amount_usd = amount * price_usd
        fiat_rates = await get_fiat_rates("USD", OUTPUT_FIAT)
        for cur, rate in fiat_rates.items():
            result[cur] = amount_usd * rate
        other = "ETH" if from_currency == "BTC" else "BTC"
        other_price = crypto_usd.get(other)
        if other_price:
            result[other] = amount_usd / other_price
    else:
        fiat_targets = [c for c in OUTPUT_FIAT if c != from_currency]
        fiat_rates = await get_fiat_rates(from_currency, fiat_targets)
        for cur, rate in fiat_rates.items():
            result[cur] = amount * rate

        if from_currency == "USD":
            usd_amount = amount
        elif "USD" in fiat_rates:
            usd_amount = amount * fiat_rates["USD"]
        else:
            usd_rates = await get_fiat_rates(from_currency, ["USD"])
            usd_amount = amount * usd_rates["USD"] if "USD" in usd_rates else None

        if usd_amount:
            crypto_usd = await get_crypto_in_usd()
            for c in OUTPUT_CRYPTO:
                price = crypto_usd.get(c)
                if price:
                    result[c] = usd_amount / price

    return result


async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    if msg.chat_id == TARGET_CHAT_ID:
        return

    logger.info(f"получено: {msg.text}")

    parsed = detect_currency(msg.text)
    if not parsed:
        await forward_message(update, context)
        return

    amount, from_currency = parsed
    logger.info(f"распознано: {amount} {from_currency}")

    wait_msg = await msg.reply_text("⏳")
    converted = await convert_all(amount, from_currency)
    await wait_msg.delete()

    if not converted:
        await msg.reply_text("Failed to get exchange rates, try again later.")
        return

    flag = "" if from_currency in ("BTC", "ETH") else CURRENCY_FLAGS.get(from_currency, "")
    sym = CURRENCY_SYMBOLS.get(from_currency, "")

    # один сплошной blockquote
    lines = []
    lines.append(f"{flag} {escape_md(format_number(amount))}{escape_md(sym)} {escape_md(from_currency)}")
    lines.append("")  # пустая строка внутри blockquote

    for cur in OUTPUT_FIAT:
        if cur in converted:
            f = CURRENCY_FLAGS.get(cur, "")
            s = CURRENCY_SYMBOLS.get(cur, "")
            lines.append(f"{f} {escape_md(format_number(converted[cur]))}{escape_md(s)} {escape_md(cur)}")

    lines.append("")  # пустая строка перед криптой
    for cur in OUTPUT_CRYPTO:
        if cur in converted:
            lines.append(f"{escape_md(format_number(converted[cur]))} {escape_md(cur)}")

    # всё в один blockquote — expandable (>>) чтобы не разбивался
    block = "**" + "\n".join(f">>{line}" if line else ">>" for line in lines) + "**"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Delete", callback_data="delete_msg")
    ]])

    try:
        sent = await context.bot.send_message(
            chat_id=msg.chat_id,
            text=block,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_to_message_id=msg.message_id,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"ошибка отправки: {e}")
        # fallback без форматирования
        plain_lines = []
        plain_lines.append(f"{flag} {format_number(amount)}{sym} {from_currency}\n")
        for cur in OUTPUT_FIAT:
            if cur in converted:
                f = CURRENCY_FLAGS.get(cur, "")
                s = CURRENCY_SYMBOLS.get(cur, "")
                plain_lines.append(f"{f} {format_number(converted[cur])}{s} {cur}")
        plain_lines.append("")
        for cur in OUTPUT_CRYPTO:
            if cur in converted:
                plain_lines.append(f"{format_number(converted[cur])} {cur}")
        await context.bot.send_message(
            chat_id=msg.chat_id,
            text="\n".join(plain_lines),
            reply_to_message_id=msg.message_id,
            reply_markup=keyboard,
        )

    try:
        forwarded = await context.bot.forward_message(
            chat_id=TARGET_CHAT_ID,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        pending_replies[forwarded.message_id] = msg.chat_id
    except Exception as e:
        logger.error(f"ошибка пересылки: {e}")


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception as e:
        logger.error(f"ошибка удаления: {e}")


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat_id == TARGET_CHAT_ID:
        return
    try:
        forwarded = await context.bot.forward_message(
            chat_id=TARGET_CHAT_ID,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        pending_replies[forwarded.message_id] = msg.chat_id
    except Exception as e:
        logger.error(f"ошибка пересылки: {e}")


async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.chat_id != TARGET_CHAT_ID:
        return
    if not msg.reply_to_message:
        return
    original_sender_id = pending_replies.get(msg.reply_to_message.message_id)
    if not original_sender_id:
        await msg.reply_text("Can't find the original sender.")
        return
    try:
        await context.bot.send_message(
            chat_id=original_sender_id,
            text=f"📩 {msg.text}"
        )
        await msg.reply_text("✅ Sent.")
    except Exception as e:
        await msg.reply_text(f"Error: {e}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💱 *Currency Converter*\n\n"
        "Just type any amount with a currency and I'll instantly convert it\\.\n\n"
        "*Examples:*\n"
        "• `200 UAH`\n"
        "• `50 USD`\n"
        "• `0\\.1 BTC`\n"
        "• `1000 ¥`\n"
        "• `500 🇩🇪`\n\n"
        "Supports 160\\+ world currencies, crypto, and flag emojis\\.\n"
        "Results include GBP, CHF, EUR, USD, UAH, RUB, BTC and ETH\\.\n\n"
        "*Commands:*\n"
        "• /currencies — full list of all supported currencies\n"
        "• /roll \[max\] — random number from 1 to 100, or set your own max\n"
        "  `/roll` → 1\-100 · `/roll 6` → 1\-6 · unlimited rolls",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # все валюты из алиасов + крипта
    all_currencies = {
        "🇬🇧 GBP": "British Pound",
        "🇨🇭 CHF": "Swiss Franc",
        "🇪🇺 EUR": "Euro",
        "🇺🇸 USD": "US Dollar",
        "🇺🇦 UAH": "Ukrainian Hryvnia",
        "🇷🇺 RUB": "Russian Ruble",
        "🇯🇵 JPY": "Japanese Yen",
        "🇨🇳 CNY": "Chinese Yuan",
        "🇰🇷 KRW": "South Korean Won",
        "🇭🇰 HKD": "Hong Kong Dollar",
        "🇸🇬 SGD": "Singapore Dollar",
        "🇦🇺 AUD": "Australian Dollar",
        "🇨🇦 CAD": "Canadian Dollar",
        "🇳🇿 NZD": "New Zealand Dollar",
        "🇸🇪 SEK": "Swedish Krona",
        "🇳🇴 NOK": "Norwegian Krone",
        "🇩🇰 DKK": "Danish Krone",
        "🇵🇱 PLN": "Polish Zloty",
        "🇨🇿 CZK": "Czech Koruna",
        "🇭🇺 HUF": "Hungarian Forint",
        "🇷🇴 RON": "Romanian Leu",
        "🇧🇬 BGN": "Bulgarian Lev",
        "🇷🇸 RSD": "Serbian Dinar",
        "🇭🇷 HRK": "Croatian Kuna",
        "🇹🇷 TRY": "Turkish Lira",
        "🇮🇱 ILS": "Israeli Shekel",
        "🇸🇦 SAR": "Saudi Riyal",
        "🇦🇪 AED": "UAE Dirham",
        "🇶🇦 QAR": "Qatari Riyal",
        "🇰🇼 KWD": "Kuwaiti Dinar",
        "🇧🇭 BHD": "Bahraini Dinar",
        "🇴🇲 OMR": "Omani Rial",
        "🇯🇴 JOD": "Jordanian Dinar",
        "🇮🇷 IRR": "Iranian Rial",
        "🇮🇶 IQD": "Iraqi Dinar",
        "🇮🇳 INR": "Indian Rupee",
        "🇵🇰 PKR": "Pakistani Rupee",
        "🇧🇩 BDT": "Bangladeshi Taka",
        "🇱🇰 LKR": "Sri Lankan Rupee",
        "🇳🇵 NPR": "Nepalese Rupee",
        "🇲🇾 MYR": "Malaysian Ringgit",
        "🇮🇩 IDR": "Indonesian Rupiah",
        "🇹🇭 THB": "Thai Baht",
        "🇻🇳 VND": "Vietnamese Dong",
        "🇵🇭 PHP": "Philippine Peso",
        "🇲🇲 MMK": "Myanmar Kyat",
        "🇰🇭 KHR": "Cambodian Riel",
        "🇱🇦 LAK": "Lao Kip",
        "🇧🇳 BND": "Brunei Dollar",
        "🇰🇿 KZT": "Kazakhstani Tenge",
        "🇺🇿 UZS": "Uzbekistani Som",
        "🇦🇲 AMD": "Armenian Dram",
        "🇬🇪 GEL": "Georgian Lari",
        "🇦🇿 AZN": "Azerbaijani Manat",
        "🇧🇾 BYN": "Belarusian Ruble",
        "🇲🇩 MDL": "Moldovan Leu",
        "🇰🇬 KGS": "Kyrgyzstani Som",
        "🇹🇯 TJS": "Tajikistani Somoni",
        "🇹🇲 TMT": "Turkmenistani Manat",
        "🇲🇳 MNT": "Mongolian Tugrik",
        "🇿🇦 ZAR": "South African Rand",
        "🇳🇬 NGN": "Nigerian Naira",
        "🇰🇪 KES": "Kenyan Shilling",
        "🇬🇭 GHS": "Ghanaian Cedi",
        "🇹🇿 TZS": "Tanzanian Shilling",
        "🇺🇬 UGX": "Ugandan Shilling",
        "🇪🇹 ETB": "Ethiopian Birr",
        "🇲🇦 MAD": "Moroccan Dirham",
        "🇩🇿 DZD": "Algerian Dinar",
        "🇹🇳 TND": "Tunisian Dinar",
        "🇱🇾 LYD": "Libyan Dinar",
        "🇪🇬 EGP": "Egyptian Pound",
        "🇧🇷 BRL": "Brazilian Real",
        "🇲🇽 MXN": "Mexican Peso",
        "🇦🇷 ARS": "Argentine Peso",
        "🇨🇱 CLP": "Chilean Peso",
        "🇨🇴 COP": "Colombian Peso",
        "🇵🇪 PEN": "Peruvian Sol",
        "🇺🇾 UYU": "Uruguayan Peso",
        "🇧🇴 BOB": "Bolivian Boliviano",
        "🇵🇾 PYG": "Paraguayan Guarani",
        "🇻🇪 VES": "Venezuelan Bolívar",
        "🇨🇺 CUP": "Cuban Peso",
        "🇩🇴 DOP": "Dominican Peso",
        "🇬🇹 GTQ": "Guatemalan Quetzal",
        "🇭🇳 HNL": "Honduran Lempira",
        "🇨🇷 CRC": "Costa Rican Colón",
        "🇵🇦 PAB": "Panamanian Balboa",
        "🇯🇲 JMD": "Jamaican Dollar",
        "🇹🇹 TTD": "Trinidad Dollar",
        "🇮🇸 ISK": "Icelandic Króna",
        "🇦🇱 ALL": "Albanian Lek",
        "🇲🇰 MKD": "Macedonian Denar",
        "🇧🇦 BAM": "Bosnia Mark",
        "₿ BTC": "Bitcoin",
        "Ξ ETH": "Ethereum",
    }

    lines = ["💱 *Supported Currencies*\n"]
    for code, name in all_currencies.items():
        lines.append(f"{code} — {name}")

    # разбиваем на два сообщения чтобы не превысить лимит
    half = len(lines) // 2
    msg1 = "\n".join(lines[:half])
    msg2 = "\n".join(lines[half:])

    await update.message.reply_text(msg1, parse_mode=ParseMode.MARKDOWN_V2)
    await update.message.reply_text(msg2)


async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    max_val = 100
    if context.args and context.args[0].isdigit():
        max_val = int(context.args[0])
    result = random.randint(1, max_val)
    await update.message.reply_text(f"🎲 {result} out of {max_val}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("currencies", cmd_currencies))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CallbackQueryHandler(delete_callback, pattern="^delete_msg$"))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    logger.info("бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()