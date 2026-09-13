import math
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram Bot Token'ın
BOT_TOKEN = "8342687226:AAFZjrDQi1kXIZw7-Y5gWEKTp3gz8la56pM"

# --- 1. RENDER'IN İSTEDİĞİ CANLI TUTMA WEB SUNUCUSU ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot 7/24 Aktif Calisiyor!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Web sunucusunu arka planda başlat
threading.Thread(target=run_web_server, daemon=True).start()

# --- 2. POISSON & ANALİZ HESAPLAMALARI ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def poisson_olasilik(lmbda, k):
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "⚽ *xG Poisson & İlk Yarı Analiz Botu*\n\n"
        "Kullanım Formatı:\n"
        "`/analiz [Ev xG] [Ev xGA] [Ev Maç] [Dep xG] [Dep xGA] [Dep Maç]`\n\n"
        "*Örnek:*\n`/analiz 8.1 3.8 3 5.9 2.7 3`"
    )
    await update.message.reply_text(mesaj, parse_mode='Markdown')

async def analiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) != 6:
            await update.message.reply_text(
                "❌ *Hatalı Girdi!*\n"
                "Lütfen 6 adet sayı girin:\n"
                "`/analiz [Ev xG] [Ev xGA] [Ev Maç] [Dep xG] [Dep xGA] [Dep Maç]`\n\n"
                "*Örnek:*\n`/analiz 8.1 3.8 3 5.9 2.7 3`",
                parse_mode='Markdown'
            )
            return

        temiz_args = [float(a.replace(',', '.')) for a in args]
        ev_toplam_xg, ev_toplam_xga, ev_mac, dep_toplam_xg, dep_toplam_xga, dep_mac = temiz_args

        if ev_mac <= 0 or dep_mac <= 0:
            await update.message.reply_text("❌ Maç sayısı 0'dan büyük olmalıdır.")
            return

        # Maç Başı Ortalamalar
        ev_hucum = ev_toplam_xg / ev_mac
        ev_savunma = ev_toplam_xga / ev_mac
        dep_hucum = dep_toplam_xg / dep_mac
        dep_savunma = dep_toplam_xga / dep_mac

        lig_ort = 1.35

        # Gol Beklentileri (Lambda)
        ev_lambda = (ev_hucum * dep_savunma) / lig_ort
        dep_lambda = (dep_hucum * ev_savunma) / lig_ort

        # İlk Yarı Beklentileri (%45)
        iy_ev_lambda = ev_lambda * 0.45
        iy_dep_lambda = dep_lambda * 0.45

        # Maç Sonu Olasılıkları
        ms_1 = ms_0 = ms_2 = ust_2_5 = kg_var = 0.0
        for i in range(7):
            for j in range(7):
                p = poisson_olasilik(ev_lambda, i) * poisson_olasilik(dep_lambda, j)
                if i > j: ms_1 += p
                elif i == j: ms_0 += p
                else: ms_2 += p
                if (i + j) > 2.5: ust_2_5 += p
                if i > 0 and j > 0: kg_var += p

        # İlk Yarı Olasılıkları & Skor Matrisi
        iy_1 = iy_0 = iy_2 = iy_ust_0_5 = iy_ust_1_5 = 0.0
        iy_skorlar = {}

        for i in range(5):
            for j in range(5):
                p_iy = poisson_olasilik(iy_ev_lambda, i) * poisson_olasilik(iy_dep_lambda, j)
                iy_skorlar[f"{i}-{j}"] = p_iy

                if i > j: iy_1 += p_iy
                elif i == j: iy_0 += p_iy
                else: iy_2 += p_iy

                if (i + j) > 0.5: iy_ust_0_5 += p_iy
                if (i + j) > 1.5: iy_ust_1_5 += p_iy

        sirali_iy_skorlar = sorted(iy_skorlar.items(), key=lambda x: x[1], reverse=True)[:3]
        skor_metni = "\n".join([f"  • *{skor}:* %{prob*100:.1f}" for skor, prob in sirali_iy_skorlar])

        # Rapor
        rapor = (
            "📊 *MAÇ & İLK YARI POISSON ANALİZİ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Gol Beklentileri (Ev / Dep):*\n"
            f"• Maç Sonu xG: `{ev_lambda:.2f}` / `{dep_lambda:.2f}`\n"
            f"• İlk Yarı xG: `{iy_ev_lambda:.2f}` / `{iy_dep_lambda:.2f}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏱️ *İLK YARI (İY) TAHMİNLERİ:*\n"
            f"• *İY 1:* %{iy_1 * 100:.1f} | *İY 0:* %{iy_0 * 100:.1f} | *İY 2:* %{iy_2 * 100:.1f}\n"
            f"• *İY 0.5 ÜST:* %{iy_ust_0_5 * 100:.1f}  (Alt: %{(1 - iy_ust_0_5) * 100:.1f})\n"
            f"• *İY 1.5 ÜST:* %{iy_ust_1_5 * 100:.1f}  (Alt: %{(1 - iy_ust_1_5) * 100:.1f})\n\n"
            f"📌 *En Olası İlk Yarı Skorları:*\n{skor_metni}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏁 *MAÇ SONU (MS) TAHMİNLERİ:*\n"
            f"• *MS 1:* %{ms_1 * 100:.1f} | *MS 0:* %{ms_0 * 100:.1f} | *MS 2:* %{ms_2 * 100:.1f}\n"
            f"• *2.5 ÜST:* %{ust_2_5 * 100:.1f}  (Alt: %{(1 - ust_2_5) * 100:.1f})\n"
            f"• *KG VAR:* %{kg_var * 100:.1f}  (Yok: %{(1 - kg_var) * 100:.1f})\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

        await update.message.reply_text(rapor, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata: {str(e)}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analiz", analiz))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
