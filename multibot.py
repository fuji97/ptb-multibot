from telegram import Bot, Update
from telegram.ext import Dispatcher
from queue import Queue
from threading import Thread
from signal import SIGINT, SIGTERM, SIGABRT, signal
from time import sleep
from flask import request
import logging
import os

logger = logging.getLogger(__name__)

class BotManager():
    """
    This is a wrapper for the Bot class
    """
    def __init__(self, token):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Creating new BotManager with token: %s", token)
        self.bot = Bot(token)
        self.name = self.bot.name
        self.update_queue = Queue()
        self.dispatcher = Dispatcher(self.bot, self.update_queue)
        self.thread = Thread(target=self.dispatcher.start, name=self.name + " dispatcher")
        self.running = False
        self.is_idle = False
        self.wb_thread = None
        self.token = token
        
    def start(self):
        self.logger.debug("Starting %s", self.name)
        self.thread.start()
        self.running = True
        
    def stop(self):
        self.logger.debug("Stopping %s", self.name)
        self.dispatcher.stop()
        self.thread.join()
        self.thread = None
        self.running = False
        
    def set_webhook(self, base_url):
        self.logger.debug("Setting webhook at %s", base_url + self.token)
        self.bot.set_webhook(base_url + self.token)

class Multibot():
    """
    This class manage all bots and the web server.
    
    Args:
        tokens (list): A list of all bot's tokens.
    """
    def __init__(self, tokens):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Creating a Multibot object...")
        self.tokens = tokens
        self.bots = {}
        self.running = False
        for token in tokens:
            self.bots[token] = BotManager(token)
    
    def dispatcher(self, token):
        """
        Get the dispatcher of a bot.
        Args:
            token (String): Token of the bot.
        """
        return self.bots[token].dispatcher
    
    def stop(self):
        """
        Stop Multibot
        """
        if self.running:
            self.logger.info('Stopping all bots...')
            self.running = False
            
            for key, bot in self.bots.items():
                bot.stop()
            
            """
            with self.app.test_request_context():
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    raise RuntimeError('Not running with the Werkzeug Server')
                func()
            """
            # TODO Force exit because I haven't found a good way to terminate
            # Flask server
            self.logger.info('All bots stopped, terminating process...')
            os._exit(0)
                
    def set_webhooks(self, base_url):
        """
        Set webhook for each bot in the object, the webhook is generated from
        the base_url + bot's token.
        Args:
            base_url (string): The URL used to generate the webhooks.
        """
        self.logger.info("Setting webhooks of all bots with base_url: %s", base_url)
        for key, bot in self.bots.items():
            bot.set_webhook(base_url)

    def signal_handler(self, signum, frame):
        self.is_idle = False
        if self.running:
            self.stop()
        else:
            self.logger.warning('Exiting immediately!')
            import os
            os._exit(1)
            
    def start(self):
        self.logger.debug("Starting all bots...")
        for key, bot in self.bots.items():
            bot.start()
        self.running = True
        self.logger.debug("%d bots started", len(self.bots))
        

    def start_webhook(self, flask_app, base_route_path='/', custom_flask_args=(), custom_flask_kwargs={}, stop_signals=(SIGINT, SIGTERM, SIGABRT)):
        """
        Start Multibot and the Flask's web server.
        Args:
            flask_app (flask.Flask): The flask's app that will be used as web server.
            base_route_path (String): Route path from where bot will be routed.
                Default is '/'.
            custom_flask_args (List): List of custom arguments used to run the
                Flask's app. Default is ().
            custom_flask_kwargs (Dict): Dict of custom keywork arguments used
                to run the Flask's app. Default is {}.
            stop_signals: Iterable containing signals from the signal module
                that should be subscribed to. Updater.stop() will be called on
                receiving one of those signals. Defaults to (SIGINT, SIGTERM,
                SIGABRT).
        """
        
        self.logger.debug("Starting bots and web server...")
        self.app = flask_app
        
        @self.app.route(base_route_path + '<token>', methods=['POST'])
        def webhook(token=None):
            try:
                bot = self.bots[token]
                bot.update_queue.put(Update.de_json(request.get_json(force=True), bot.bot))
                return 'ok'
            except Exception:
                self.logger.error("Received an invalid token request: %s", token)
                return 'Invalid token'   
        
        for sig in stop_signals:
            signal(sig, self.signal_handler)

        self.is_idle = True
        self.start()
        self.logger.info("Multbot started with %d bots", len(self.bots))

        self.app.run(*custom_flask_args, **custom_flask_kwargs)