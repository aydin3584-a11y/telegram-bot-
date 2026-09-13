import os
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Telegram Bot Token
TOKEN = os.getenv("TELEGRAM_TOKEN", "8342687226:AAFZjrDQi1kXIZw7-Y5gWEKTp3gz8la56pM")

def poisson_prob(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calculate_probabilities(home_xg, away_xg):
    max_goals = 10
    matrix = [[poisson_prob(home_xg, h) * poisson_prob(away_xg, a) for a in range(max_goals)] for h in range(max_goals)]
    
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_2_5 = 0.0
    btts_yes = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            prob = matrix[h][a]
            if h > a:
                home_win += prob
            elif h == a:
                draw += prob
            else:
                away_win += prob

            if h + a > 2.5:
                over_2_5 += prob

            if h > 0 and a > 0:
                btts_yes += prob

    return {
        "ms1": home_win * 100,
        "ms0": draw * 100,
        "ms2": away_win * 100,
        "over25": over_2_5 * 100,
        "under25": (1 - over_2_5) * 100,
        "btts": btts_yes * 100
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Futbol xG Analiz Botuna Hoş Geldiniz!\n\n"
        "Analiz için ev sahibi ve deplasman xG değerlerini aralarında boşluk bırakarak gönderin.\n"
        "Örnek: 1.85 1.20"
    )
    await update.message.reply_text(msg)

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text("Hatalı format. Lütfen ev ve deplasman xG değerini girin.\nÖrnek: 1.85 1.20")
        return

    try:
        home_xg = float(parts[0])
        away_xg = float(parts[1])
    except ValueError:
        await update.message.reply_text("Lütfen geçerli sayılar girin.")
        return

    res = calculate_probabilities(home_xg, away_xg)

    response = (
        f"📊 Maç Analiz Sonuçları\n"
        f"Ev xG: {home_xg} | Dep xG: {away_xg}\n\n"
        f"🔹 1 (Ev Sahibi): %{res['ms1']:.1f}\n"
        f"🔹 X (Beraberlik): %{res['ms0']:.1f}\n"
        f"🔹 2 (Deplasman): %{res['ms2']:.1f}\n\n"
        f"⚽ 2.5 Üst: %{res['over25']:.1f}\n"
        f"⚽ 2.5 Alt: %{res['under25']:.1f}\n"
        f"🎯 Karşılıklı Gol Var: %{res['btts']:.1f}"
    )
    await update.message.reply_text(response)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    
    print("Bot calisiyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
