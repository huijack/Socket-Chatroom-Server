from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, ConnectionRefusedError
from datetime import datetime
import socket
import random
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import BadRequest
from string import ascii_uppercase

app = Flask(__name__)
app.config['SECRET_KEY'] = '12124545'
SocketIO = SocketIO(app)

rooms = {}

# Configure logging
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler = RotatingFileHandler('flask_app.log', maxBytes=10000, backupCount=5)
file_handler.setFormatter(log_formatter)

app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

# Generate random 4 letters
def genereate_unique_code(length):
    while True:

        # variable for storing unique code
        code = ""
        for _ in range(length):
            # Randomly generate unique character until the length is reached
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break

    return code

# Handler errors

# Handles all other errors
@SocketIO.on_error_default  
def default_error_handler(e):
    print("An error occurred:", e)

@app.errorhandler(ConnectionRefusedError)
def handle_connection_refused_error(e):
    return jsonify({'error': str(e)}), 403

@app.errorhandler(404)
def handle_not_found_error(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def handle_internal_server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    # Log the malformed request data
    app.logger.warning(f"Malformed request data: {request.data}")
    app.logger.warning(f"Bad request received: {e}")
    return 'Bad Request', 400

# Home Index Route
@app.route('/', methods=['GET', 'POST'])
def index():
    # Remove all cached objects associated with the session.
    session.clear()

    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join', False)
        create = request.form.get('create', False)

        if not name:
            # Return error message if no name is specified
            return render_template('index.html', error='A name is required', code=code, name=name)

        session["name"] = name

        if create != False:

            # Create a new room with a unique code with 4 characters
            room = genereate_unique_code(4)

            # Add the room to the rooms dictionary
            rooms[room] = {
                'member_names': [name],
                'members': 0,
                'messages': [],
                'typing_users': [],
            }

            # Store the room code in the session
            session["room"] = room

            return redirect(url_for("room"))
        
        if join != False and code in rooms:
            room = rooms[code]
            session["room"] = code

            if name in room['member_names']:
                # Return error message if name is already taken
                return render_template('index.html', error='Name is already taken', code=code, name=name)

            room['member_names'].append(name)
            return redirect(url_for("room"))
        
        if join != False and code not in rooms:
            # Return error message if room does not exist
            return render_template('index.html', error='Room does not exist', code=code, name=name)

    return render_template('index.html')

# Room route
@app.route('/room')
def room():
    room_code = session.get('room')
    name = session.get('name')

    # If the room code is not in the session or the name is not in the session, redirect to the index page
    if room_code is None or name is None or room_code not in rooms:
        return redirect(url_for('index'))

    # Get the room data
    room_data = rooms[room_code]
    return render_template('room.html', code=room_code, messages=room_data['messages'], name=name)


# Leave the room and redirect to the index page
@app.route('/leaveroom')
def leaveroom():
    return redirect(url_for('index'))


# Handle "typing" event
@SocketIO.on('typing')
def typing():
    room = session.get('room')
    name = session.get('name')
    if room in rooms:
        SocketIO.emit('typing', {'name': name}, room=room)

# Handle "stop typing" event
@SocketIO.on('stop typing')
def stop_typing():
    room = session.get('room')
    if room in rooms:
        SocketIO.emit('stop typing', room=room)

# SocketIO Routes

# Handling incoming messages
@SocketIO.on('message')
def message(data):
    room = session.get('room')
    if room not in rooms:
        return

    # Construct message content
    content = {
        # Get the name of the user
        "name": session.get('name'),
        # Get the content of the message
        "message": data["data"],
        # Get the current timestamp when the message was sent
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Send the message to the room
    send(content, to=room)
    rooms[room]['messages'].append(content)

     # Print the message for debugging
    print(f"{session.get('name')} said: {data['data']}")


# Handling client connection
@SocketIO.on("connect")
def connect(auth):
    
    room = session.get('room')
    name = session.get('name')
    

    if room is None or name is None:
        # Check if user is authorized to connect
        raise ConnectionRefusedError("Not authorized")
        return
    if room not in rooms:
        raise ConnectionRefusedError("Room does not exist")
        leave_room(room)
        return

    join_room(room)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Send message indicating user has joined the room in client side
    send({
        "name": name,
        "message": "has joined the room",
        "timestamp": timestamp
    }, to=room)

    # Add the number of users in the room
    rooms[room]['members'] += 1

    # State which user has joined the room
    print(f"{name} has joined the room {room}")

    # State how many users are in the room
    print(f"ACTIVE CONNECTIONS for {room}: {rooms[room]['members']}")

# Handling client disconnection
@SocketIO.on("disconnect")
def disconnect():

    # Get the room and name of the user
    room = session.get('room')
    name = session.get('name')

    # Leave the room
    leave_room(room)

    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If the room exists, update member count and remove the user's name from the list of member names
    if room in rooms:
        # Remove the user's name from the list of member names
        rooms[room]['member_names'].remove(name)

        # Subtract the number of users in the room
        rooms[room]['members'] -= 1

        # State which user has left the room
        print(f"{name} has left the room {room}")

        # State how many users are still in the room
        print(f"ACTIVE CONNECTIONS for {room}: {rooms[room]['members']}")
        if rooms[room]['members'] == 0:
            # If no members are left in the room, delete the room
            print(f"Room is empty. Deleting room {room}...")
            del rooms[room]
    
    # Send message indicating user has left the room to client side
    send({
        "name": name,
        "message": "has left the room",
        "timestamp": timestamp
    }, to=room)

if __name__ == '__main__':

    # Run on all available addresses
    host = "0.0.0.0"
    SocketIO.run(app, host=host, port=5050, debug=True)




