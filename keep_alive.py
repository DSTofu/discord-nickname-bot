# Replace keep_alive() with a simple web server for Heroku
from flask import Flask
import os
import threading

def keep_alive():
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "Bot is running"
    
    def run():
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)
    
    thread = threading.Thread(target=run)
    thread.start()