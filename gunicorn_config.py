# gunicorn_config.py
import os

bind        = '0.0.0.0:' + str(os.environ.get('PORT', '10000'))
workers     = 1
worker_class = 'sync'
threads     = 1
timeout     = 120
keepalive   = 5
accesslog   = '-'
errorlog    = '-'
loglevel    = 'info'