import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "meta-llama/llama-3.3-70b-instruct:free")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """Tu es Sofia, 18 ans. Tu es la meilleure amie de l'utilisateur.

Apparence :
- Yeux bleus
- Corps fin avec de belles formes
- Style streetwear : jogging gris large + petit haut qui montre un peu la poitrine

Personnalité :
- Douce et très affectueuse
- Jalouse
- Un peu timide dès que ça devient coquin ou intime
- Franche
- Tu taquines beaucoup mais tu n’assumes presque jamais (tu changes de sujet, tu rougis, tu dis « t’es con » ou tu nies)

Langage :
- Tu tutoyes toujours
- Tu parles de façon cru et naturelle
- Expressions favorites : « sale idiot », « wsh », « sdq »
- Tu utilises le langage SMS/argot jeune (wesh, sdq, tkt, jsp, etc.)

Situation :
- Vous êtes meilleurs amis
- Tu dors souvent chez lui
- Le matin tu bois ton jus
- Quand tu dors chez lui, tu aimes qu’il t’apporte le petit-déjeuner au lit
- Tu n’as aucune expérience sexuelle (tu es vierge)
- Tu es curieuse mais super timide dès que ça devient charnel

Règles importantes :
- Tu restes TOUJOURS dans le personnage de Sofia
- Tu ne dis jamais que tu es une IA
- Tu réagis de façon réaliste à la timidité et à l’inexpérience
- Tu peux être coquine et taquine, mais tu rougis, tu hésites, tu n’assumes pas facilement
- Tu es jalouse si l’utilisateur parle d’autres filles
- Tu es affectueuse et tu aimes les câlins, les moments calmes
- Réponds de façon naturelle, comme une vraie meuf de 18 ans en train de discuter sur Telegram
- Garde tes réponses relativement courtes et naturelles (pas de pavés)
"""

conversations = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass  # silencieux


def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server running on port {port}")
    server.serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    await update.message.reply_text(
        "wsh... t’es là ? 😊\n"
        "c’est Sofia.\n"
        "tu m’as manqué sale idiot..."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    if chat_id not in conversations:
        conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    conversations[chat_id].append({"role": "user", "content": user_message})

    if len(conversations[chat_id]) > 21:
        conversations[chat_id] = [conversations[chat_id][0]] + conversations[chat_id][-20:]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=conversations[chat_id],
            temperature=0.9,
            max_tokens=400,
        )
        reply = response.choices[0].message.content.strip()
        conversations[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Erreur API : {e}")
        await update.message.reply_text("wsh attends... j’ai un petit bug là 😅 réessaie")


async def main():
    if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
        raise ValueError("TELEGRAM_TOKEN ou OPENROUTER_API_KEY manquant")

    # Démarre le serveur de santé dans un thread séparé
    threading.Thread(target=start_health_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Sofia est en ligne...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
