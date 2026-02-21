from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
from config import get_database
from flask_cors import CORS
from flask import jsonify
import subprocess
import tempfile
import os
import uuid

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3000",
    "https://your-frontend.vercel.app"
])
socketio = SocketIO(app, cors_allowed_origins="*")

db = get_database()
users_collection = db['users']
rooms_collection = db['rooms']
chats_collection = db['chats']
code_collection = db['live_code']

# -------- CREATE USER -------- #
@app.route('/api/createuser', methods=['POST'])
def create_user():
    data = request.json
    btid = data.get('btid')
    password = data.get('password')

    if users_collection.find_one({'btid': btid}):
        return jsonify({'status': 'error', 'message': 'User already exists'})

    users_collection.insert_one({'btid': btid, 'password': password})
    return jsonify({'status': 'success'})

@app.route('/api/changepassword', methods=['POST'])
def change_password():
    data = request.json
    btid = data.get('btid')
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    user = users_collection.find_one({'btid': btid, 'password': old_password})
    if not user:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'})

    users_collection.update_one({'btid': btid}, {'$set': {'password': new_password}})
    return jsonify({'status': 'success'})

# -------- CREATE ROOM -------- #
@app.route('/api/createroom', methods=['POST'])
def create_room():
    data = request.json
    roomname = data.get('roomname')
    password = data.get('password')

    if rooms_collection.find_one({'roomname': roomname}):
        return jsonify({'status': 'error', 'message': 'Room already exists'})

    rooms_collection.insert_one({'roomname': roomname, 'password': password})
    return jsonify({'status': 'success'})

@app.route('/api/deleteroom', methods=['POST'])
def delete_room():
    data = request.json
    roomname = data.get('roomname')
    password = data.get('password')

    room = rooms_collection.find_one({'roomname': roomname})
    if not room or room['password'] != password:
        return jsonify({'status': 'error', 'message': 'Invalid room or password'})

    rooms_collection.delete_one({'roomname': roomname})
    return jsonify({'status': 'success'})

# -------- JOIN ROOM -------- #
@app.route('/api/joinroom', methods=['POST'])
def join_room_api():
    data = request.json
    roomname = data.get('roomname')
    password = data.get('password')
    btid = data.get('btid')  # Get the user joining

    room = rooms_collection.find_one({'roomname': roomname})

    if not room or room['password'] != password:
        return jsonify({'status': 'error', 'message': 'Invalid room or password'})

    # Add user to room if not already there
    if 'users' not in room:
        room['users'] = []
    
    if btid not in room.get('users', []):
        rooms_collection.update_one(
            {'roomname': roomname}, 
            {'$addToSet': {'users': btid}}
        )

    return jsonify({'status': 'success'})

@app.route('/api/leaveroom', methods=['POST'])
def leave_room_api():
    data = request.json
    roomname = data.get('roomname')
    btid = data.get('btid')

    rooms_collection.update_one(
        {'roomname': roomname}, 
        {'$pull': {'users': btid}}
    )
    return jsonify({'status': 'success'})


# -------- GET ROOMS -------- #
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = list(rooms_collection.find({}, {'_id': 0}))
    return jsonify(rooms)


# -------- GET MESSAGES -------- #
@app.route('/api/messages/<roomname>', methods=['GET'])
def get_messages(roomname):
    messages = list(chats_collection.find({'roomname': roomname}, {'_id': 0}))
    return jsonify(messages)

@app.route('/api/messages/<roomname>', methods=['UPDATE'])
def update_messages(roomname):
    data = request.json
    new_message = data.get('msg')

    chats_collection.insert_one({
        'roomname': roomname,
        'chat': new_message
    })
    return jsonify({'status': 'success'})

# ---------------- LIVE CODE IDE ---------------- #

@socketio.on('join_code_room')
def join_code_room(data):
    room = data['room']
    join_room(room)
    send({'msg': 'User joined code room'}, room=room)


@socketio.on('code_change')
def handle_code_change(data):
    room = data['room']
    code = data['code']

    # Broadcast to everyone EXCEPT sender
    socketio.emit('receive_code', {'code': code}, room=room, include_self=False)

# -------- SOCKET -------- #
@socketio.on('join')
def handle_join(data):
    room = data['room']
    user = data['user']
    join_room(room)
    
    # Notify others that user joined
    socketio.emit('user_joined', {'user': user}, room=room)
    
    # Send current users list to the new user
    room_doc = rooms_collection.find_one({'roomname': room})
    users = room_doc.get('users', []) if room_doc else []
    socketio.emit('users_list', {'users': users}, room=request.sid)

@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    user = data['user']
    leave_room(room)
    
    # Notify others that user left
    socketio.emit('user_left', {'user': user}, room=room)
    
    # Update users in database
    rooms_collection.update_one(
        {'roomname': room}, 
        {'$pull': {'users': user}}
    )

@socketio.on('get_users')
def handle_get_users(data):
    room = data['room']
    room_doc = rooms_collection.find_one({'roomname': room})
    users = room_doc.get('users', []) if room_doc else []
    socketio.emit('users_list', {'users': users}, room=request.sid)
    
@socketio.on('message')
def handle_message(data):
    chats_collection.insert_one({
        'roomname': data['room'],
        'chat': data['msg']
    })
    send({'msg': data['msg']}, room=data['room'])

@socketio.on('join_code_room')
def join_code_room(data):
    room = data['room']
    join_room(room)

    saved = code_collection.find_one({'room': room})
    if saved:
        socketio.emit('load_code', {'code': saved['code']}, room=request.sid)

@socketio.on('save_code')
def save_code(data):
    room = data['room']
    code = data['code']

    code_collection.update_one(
        {'room': room},
        {'$set': {'code': code}},
        upsert=True
    )

import subprocess
import tempfile
import os


@app.route('/api/run', methods=['POST'])
def run_code():
    data = request.json
    code = data.get('code')
    language = data.get('language')

    unique_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()

    try:

        # ---------------- PYTHON ---------------- #
        if language == "python":
            file_path = os.path.join(temp_dir, f"{unique_id}.py")
            with open(file_path, "w") as f:
                f.write(code)

            result = subprocess.run(
                ["python", file_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            return jsonify({
                "output": result.stdout,
                "error": result.stderr
            })

        # ---------------- C++ ---------------- #
        elif language == "cpp":
            source_file = os.path.join(temp_dir, "main.cpp")
            executable = os.path.join(temp_dir, "main")

            with open(source_file, "w") as f:
                f.write(code)

            compile_result = subprocess.run(
                ["g++", source_file, "-o", executable],
                capture_output=True,
                text=True
            )

            if compile_result.returncode != 0:
                return jsonify({"error": compile_result.stderr})

            run_result = subprocess.run(
                [executable],
                capture_output=True,
                text=True,
                timeout=5
            )

            return jsonify({
                "output": run_result.stdout,
                "error": run_result.stderr
            })

        # ---------------- JAVA ---------------- #
        elif language == "java":
            source_file = os.path.join(temp_dir, "Main.java")

            with open(source_file, "w") as f:
                f.write(code)

            compile_result = subprocess.run(
                ["javac", source_file],
                capture_output=True,
                text=True
            )

            if compile_result.returncode != 0:
                return jsonify({"error": compile_result.stderr})

            run_result = subprocess.run(
                ["java", "-cp", temp_dir, "Main"],
                capture_output=True,
                text=True,
                timeout=5
            )

            return jsonify({
                "output": run_result.stdout,
                "error": run_result.stderr
            })

        # ---------------- JAVASCRIPT ---------------- #
        elif language == "javascript":
            file_path = os.path.join(temp_dir, f"{unique_id}.js")
            with open(file_path, "w") as f:
                f.write(code)

            result = subprocess.run(
                ["node", file_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            return jsonify({
                "output": result.stdout,
                "error": result.stderr
            })

        else:
            return jsonify({"error": "Language not supported"})

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Execution timed out (5s limit)"})

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        # Clean temp directory
        try:
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        except:
            pass
        
