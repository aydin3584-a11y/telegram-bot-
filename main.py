import os
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. RENDER PORT VE CANLI TUTMA SUNUCUSU ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot 7/24 Aktif!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- 2. MATEMATİKSEL FONKSİYONLAR ---
def poisson(k, lamb):
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)

def analiz_motoru(ev_ad, dep_ad, ev_xg, dep_xg, oran=None):
    # 90 Dakika Matrisi
    matrix_ms = {}
    for i in range(7):
        for j in range(7):
            matrix_ms[(i, j)] = poisson(i, ev_xg) * poisson(j, dep_xg)

    # İlk Yarı (İY) Yaklaşımı (Genelde gollerin %45'i ilk yarıda olur)
    ev_iy_xg = ev_xg * 0.45
    dep_iy_xg = dep_xg * 0.45
    matrix_iy = {}
    for i in range(4):
        for j in range(4):
            matrix_iy[(i, j)] = poisson(i, ev_iy_xg) * poisson(j, dep_iy_xg)

    # MS İhtimalleri
    ms1 = sum(p for (i, j), p in matrix_ms.items() if i > j) * 100
    ms0 = sum(p for (i, j), p in matrix_ms.items() if i == j) * 100
    ms2 = sum(p for (i, j), p in matrix_ms.items() if i < j) * 100

    # Çifte Şans
    cs_1x = ms1 + ms0
    cs_x2 = ms0 + ms2
    cs_12 = ms1 + ms2

    # İY İhtimalleri
    iy1 = sum(p for (i, j), p in matrix_iy.items() if i > j) * 100
    iy0 = sum(p for (i, j), p in matrix_iy.items() if i == j) * 100
    iy2 = sum(p for (i, j), p in matrix_iy.items() if i < j) * 100
    iy_ust_05 = sum(p for (i, j), p in matrix_iy.items() if (i + j) > 0.5) * 100
    iy_ust_15 = sum(p for (i, j), p in matrix_iy.items() if (i + j) > 1.5) * 100

    # Alt / Üst Baremleri
    ust_15 = sum(p for (i, j), p in matrix_ms.items() if (i + j) > 1.5) * 100
    ust_25 = sum(p for (i, j), p in matrix_ms.items() if (i + j) > 2.5) * 100
    ust_35 = sum(p for (i, j), p in matrix_ms.items() if (i + j) > 3.5) * 100

    # KG İhtimalleri
    kg_var = sum(p for (i, j), p in matrix_ms.items() if i > 0 and j > 0) * 100
    kg_yok = 100 - kg_var

    # En Olası Skorlar
    en_olasi_skorlar = sorted(matrix_ms.items(), key=lambda x: x[1], reverse=True)[:4]

    rapor = (
        f"🎯 **PRO MAÇ ANALİZİ**\n"
        f"⚽ **{ev_ad.upper()} vs {dep_ad.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **Maç Sonucu (MS):**\n"
        f"• 1: %{ms1:.1f} | X: %{ms0:.1f} | 2: %{ms2:.1f}\n"
        f"• Çifte Şans: 1X: %{cs_1x:.1f} | X2: %{cs_x2:.1f} | 1-2: %{cs_12:.1f}\n\n"
        f"⏱️ **İlk Yarı (İY):**\n"
        f"• İY 1: %{iy1:.1f} | İY X: %{iy0:.1f} | İY 2: %{iy2:.1f}\n"
        f"• İY 0.5 Üst: %{iy_ust_05:.1f} | İY 1.5 Üst: %{iy_ust_15:.1f}\n\n"
        f"🎯 **Gol Baremleri:**\n"
        f"• 1.5 Üst: %{ust_15:.1f} | Alt: %{100 - ust_15:.1f}\n"
        f"• 2.5 Üst: %{ust_25:.1f} | Alt: %{100 - ust_25:.1f}\n"
        f"• 3.5 Üst: %{ust_35:.1f} | Alt: %{100 - ust_35:.1f}\n\n"
        f"🔥 **Karşılıklı Gol:**\n"
        f"• KG Var: %{kg_var:.1f} | KG Yok: %{kg_yok:.1f}\n\n"
        f"📌 **En Olası Skorlar:**\n"
    )
    for (i, j), prob in en_olasi_skorlar:
        rapor += f"• {i} - {j} ➔ %{prob * 100:.1f}\n"

    # Value Bet ve Kelly Hesabı (Eğer oran verildiyse)
    if oran:
        prob_ms1 = ms1 / 100
        fair_odd = 1 / prob_ms1 if prob_ms1 > 0 else 99
        b = oran - 1
        q = 1 - prob_ms1
        kelly = ((b * prob_ms1) - q) / b if b > 0 else 0
        
        rapor += f"\n💰 **VALUE BET & KASA YÖNETİMİ:**\n"
        rapor += f"• Verilen Oran: {oran:.2f} | Adil Oran: {fair_odd:.2f}\n"
        if oran > fair_odd:
            kasa_yuzde = max(0, kelly * 100 * 0.5) # Fractional Kelly (%50 güvenli)
            rapor += f"✅ **DEĞERLİ BAHİS!**\n• Önerilen Kasa Girişi: %{kasa_yuzde:.1f}\n"
        else:
            rapor += "❌ **Değersiz Oran (Pas Geçiniz)**\n"

    return rapor

# --- 3. TELEGRAM HANDLERLARI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 **Gelişmiş İddaa Analiz Robotuna Hoş Geldiniz!**\n\n"
        "**Kullanım Şekilleri:**\n"
        "1️⃣ **Hızlı Analiz:**\n"
        "`/analiz 1.80 1.20`\n\n"
        "2️⃣ **Takım İsimli Analiz:**\n"
        "`/analiz Arsenal Chelsea 1.80 1.20`\n\n"
        "3️⃣ **Value Bet & Kasa Analizli (Oran Ekleyerek):**\n"
        "`/analiz Arsenal Chelsea 1.80 1.20 2.10`\n"
        "*(En sondaki 2.10 iddaa'nın ev sahibine açtığı orandır)*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Lütfen en azından xG değerlerini girin!\nÖrnek: `/analiz 1.70 1.10` veya `/analiz Arsenal Chelsea 1.70 1.10`",
            parse_mode="Markdown"
        )
        return

    try:
        # Sadece sayılar girildiyse: /analiz 1.70 1.10
        if len(args) == 2:
            ev_ad, dep_ad = "Ev Sahibi", "Deplasman"
            ev_xg = float(args[0].replace(",", "."))
            dep_xg = float(args[1].replace(",", "."))
            oran = None
        # Takım isimleriyle: /analiz Arsenal Chelsea 1.70 1.10
        elif len(args) == 4:
            ev_ad, dep_ad = args[0], args[1]
            ev_xg = float(args[2].replace(",", "."))
            dep_xg = float(args[3].replace(",", "."))
            oran = None
        # Oran ile: /analiz Arsenal Chelsea 1.70 1.10 2.05
        elif len(args) == 5:
            ev_ad, dep_ad = args[0], args[1]
            ev_xg = float(args[2].replace(",", "."))
            dep_xg = float(args[3].replace(",", "."))
            oran = float(args[4].replace(",", "."))
        else:
            await update.message.reply_text("Formatı kontrol edin. Örnek: `/analiz Arsenal Chelsea 1.70 1.10`", parse_mode="Markdown")
            return

        cevap = analiz_motoru(ev_ad, dep_ad, ev_xg, dep_xg, oran)
        await update.message.reply_text(cevap, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("Hata! xG ve oran değerlerini sayı olarak girdiğinizden emin olun (örn: 1.5).")

# --- 4. BAŞLATICI ---
def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analiz", analiz_cmd))

    print("Gelişmiş Bot Başlatıldı...")
    app.run_polling()

if __name__ == "__main__":
    main()
