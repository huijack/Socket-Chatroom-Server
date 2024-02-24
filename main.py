from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, ConnectionRefusedError
from datetime import datetime
import socket
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config['SECRET_KEY'] = '12124545'
SocketIO = SocketIO(app)

rooms = {}

def genereate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break

    return code

@app.route('/', methods=['GET', 'POST'])
def index():
    session.clear()

    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join', False)
        create = request.form.get('create', False)

        if not name:
            return render_template('index.html', error='A name is required', code=code, name=name)

        if join != False and not code:
            return render_template('index.html', error='A code is required', code=code, name=name)

        room = code
        if create != False:
            room = genereate_unique_code(4)
            rooms[room] = {
                'members': 0,
                'messages': []
            }
        elif code not in rooms:
            return render_template('index.html', error='Room does not exist', code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template('index.html')

@app.route('/room')
def room():
    room = session.get('room')
    if room is None or session.get('name') is None or room not in rooms:
        return redirect(url_for('index'))

    return render_template('room.html', code=room, messages=rooms[room]['messages'])


@SocketIO.on('message')
def message(data):
    room = session.get('room')
    if room not in rooms:
        return

    content = {
        "name": session.get('name'),
        "message": data["data"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    send(content, to=room)
    rooms[room]['messages'].append(content)
    print(f"{session.get('name')} said: {data['data']}")


@SocketIO.on("connect")
def connect(auth):
    room = session.get('room')
    name = session.get('name')
    if room is None or name is None:
        raise ConnectionRefusedError("Not authorized")
        return
    if room not in rooms:
        raise ConnectionRefusedError("Room does not exist")
        leave_room(room)
        return
    
    join_room(room)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send({
        "name": name,
        "message": "has joined the room",
        "timestamp": timestamp
    }, to=room)
    rooms[room]['members'] += 1
    print(f"{name} has joined the room {room}")

@SocketIO.on("disconnect")
def disconnect():
    room = session.get('room')
    name = session.get('name')
    leave_room(room)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if room in rooms:
        rooms[room]['members'] -= 1
        if rooms[room]['members'] == 0:
            del rooms[room]
    
    send({
        "name": name,
        "message": "has left the room",
        "timestamp": timestamp
    }, to=room)
    print(f"{name} has left the room {room}")

if __name__ == '__main__':

    host = "192.168.1.103"
    SocketIO.run(app, host=host, port=5000, debug=True)




