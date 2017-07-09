from multibot import *
from flask import Flask, request
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from telegram import Update, Bot
import os
from threading import Thread
from queue import Queue
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(thread)d - %(message)s',
                    level=logging.INFO)

TOKENS = ['437894347:AAEmadhGMPjSF1BtRLad5NXTkRuiW-aIelc',
          '348346863:AAFFhArwcCEax0BVn4u0hHfVg-z7ZgTcCrc',]
HOOK_URL = "https://flask-bot-test-fuji97.c9users.io/test/"

def echo(bot, update):
    update.message.reply_text(update.message.text)

app = Flask(__name__)
multibot = Multibot(TOKENS)
multibot.dispatcher(TOKENS[0]).add_handler(MessageHandler(Filters.text, echo))
multibot.dispatcher(TOKENS[1]).add_handler(MessageHandler(Filters.text, echo))

multibot.set_webhooks(HOOK_URL)
multibot.start_webhook(app, '/test/', (os.getenv('IP', '0.0.0.0'), os.getenv('PORT', 8080)))
