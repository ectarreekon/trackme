# Gunicorn WSGI Configuration (gunicorn.conf.py)
workers = 4
bind = "0.0.0.0:5000"
worker_class = "gevent"
timeout = 120