import os
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. RENDER PORT UYARISINI ÇÖZEN HAFİF WEB SUNUCUSU ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot 7/24 Aktif!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- 2. POISSON VE ANALİZ HESAPLAMALARI ---
def poisson(k, lamb):
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)

def analiz_yap(ev_xg, dep_xg):
    # Skor matrisi (0-5 gol arası)
    matrix = {}
    for i in range(6):
        for j in range(6):
            matrix[(i, j)] = poisson(i, ev_xg) * poisson(j, dep_xg)

    # İhtimaller
    ms1 = sum(prob for (i, j), prob in matrix.items() if i > j) * 100
    ms0 = sum(prob for (i, j), prob in matrix.items() if i == j) * 100
    ms2 = sum(prob for (i, j), prob in matrix.items() if i < j) * 100

    ust_15 = sum(prob for (i, j), prob in matrix.items() if (i + j) > 1.5) * 100
    ust_25 = sum(prob for (i, j), prob in matrix.items() if (i + j) > 2.5) * 100
    ust_35 = sum(prob for (i, j), prob in matrix.items() if (i + j) > 3.5) * 100

    kg_var = sum(prob for (i, j), prob in matrix.items() if i > 0 and j > 0) * 100
    kg_yok = 100 - kg_var

    # En olası 3 skor
    en_olasi_skorlar = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:3]

    rapor = (
        f"📊 **MAÇ ANALİZ RAPORU**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚽ **Maç Sonucu İhtimalleri:**\n"
        f"• MS 1: %{ms1:.1f}\n"
        f"• MS X: %{ms0:.1f}\n"
        f"• MS 2: %{ms2:.1f}\n\n"
        f"🎯 **Gol Baremleri:**\n"
        f"• 1.5 Üst: %{ust_15:.1f} | Alt: %{100 - ust_15:.1f}\n"
        f"• 2.5 Üst: %{ust_25:.1f} | Alt: %{100 - ust_25:.1f}\n"
        f"• 3.5 Üst: %{ust_35:.1f} | Alt: %{100 - ust_35:.1f}\n\n"
        f"🔥 **Karşılıklı Gol:**\n"
        f"• KG Var: %{kg_var:.1f}\n"
        f"• KG Yok: %{kg_yok:.1f}\n\n"
        f"📌 **En Yüksek Olasılıklı Skorlar:**\n"
    )
    for (i, j), prob in en_olasi_skorlar:
        rapor += f"• {i} - {j} (İhtimal: %{prob * 100:.1f})\n"

    return rapor

# --- 3. TELEGRAM KOMUTLARI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "Merhaba! İddaa Analiz Botuna Hoş Geldiniz.\n\n"
        "Analiz yapmak için şu formatta gönderin:\n"
        "`/analiz Ev_xG Dep_xG`\n\n"
        "Örnek:\n"
        "`/analiz 1.75 1.10`"
    )
    await update.message.reply_text(mesaj, parse_mode="Markdown")

async def analiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Lütfen ev ve deplasman xG değerlerini girin.\nÖrnek: `/analiz 1.65 1.20`", parse_mode="Markdown")
            return
        
        ev_xg = float(context.args[0].replace(",", "."))
        dep_xg = float(context.args[1].replace(",", "."))

        sonuc = analiz_yap(ev_xg, dep_xg)
        await update.message.reply_text(sonuc, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("Hata oluştu! Değerleri sayı olarak girdiğinizden emin olun (örn: 1.5).")

# --- 4. ÇALIŞTIRMA ---
def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analiz", analiz_cmd))

    print("Bot basariyla baslatildi...")
    app.run_polling()

if __name__ == "__main__":
    main()
