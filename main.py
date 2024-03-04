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

        session["name"] = name

        if create != False:
            room = genereate_unique_code(4)
            rooms[room] = {
                'creator_name': name,
                'member_names': [name],
                'members': 0,
                'messages': []
            }
            session["room"] = room
            session["is_creator"] = True
            return redirect(url_for("room"))
        
        if join != False and code in rooms:
            room = rooms[code]
            session["room"] = code

            if name in room['member_names']:
                return render_template('index.html', error='Name is already taken', code=code, name=name)

            room['member_names'].append(name)
            session["is_creator"] = False
            return redirect(url_for("room"))
        
        if join != False and code not in rooms:
            return render_template('index.html', error='Room does not exist', code=code, name=name)

    return render_template('index.html')

@app.route('/room')
def room():
    room_code = session.get('room')
    name = session.get('name')
    is_creator = session.get('is_creator')

    if room_code is None or name is None or room_code not in rooms:
        return redirect(url_for('index'))

    if is_creator:
        name = rooms[room_code]['creator_name']

    room_data = rooms[room_code]
    return render_template('room.html', code=room_code, messages=room_data['messages'], name=name)



@app.route('/leaveroom')
def leaveroom():
    return redirect(url_for('index'))


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
    print(f"ACTIVE CONNECTIONS for {room}: {rooms[room]['members']}")

@SocketIO.on("disconnect")
def disconnect():
    room = session.get('room')
    name = session.get('name')
    leave_room(room)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if room in rooms:
        rooms[room]['members'] -= 1
        print(f"{name} has left the room {room}")
        print(f"ACTIVE CONNECTIONS for {room}: {rooms[room]['members']}")
        if rooms[room]['members'] == 0:
            print(f"Room is empty. Deleting room {room}...")
            del rooms[room]
    
    send({
        "name": name,
        "message": "has left the room",
        "timestamp": timestamp
    }, to=room)

if __name__ == '__main__':
    host = "0.0.0.0"
    SocketIO.run(app, host=host, port=5000, debug=True)




