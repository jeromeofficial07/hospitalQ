from app import socketio
from flask_socketio import emit, join_room

@socketio.on('connect')
def on_connect():
    emit('connected', {'msg': 'Connected to QueueFlow live server'})

@socketio.on('join_queue')
def on_join(data):
    room = f"queue_{data['queue_id']}"
    join_room(room)
    emit('joined', {'room': room})

@socketio.on('disconnect')
def on_disconnect():
    pass