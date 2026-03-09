

from src.loger import log

async def feedback(bot, message, send_message):
    callback = await bot.reply_to_message(message, send_message)
    log(f"{callback}", needPrint=(bot.testMode))