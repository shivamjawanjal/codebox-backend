from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, send
from config import get_database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app)

# Database setup
db = get_database()
users_collection = db['users']
chats_collection = db['chats']
rooms_collection = db['rooms']


# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')


# -------- CREATE USER -------- #
@app.route('/createuser', methods=['POST'])
def create_user():
    btid = request.form.get('btid')
    password = request.form.get('password')

    if not btid or not password:
        return render_template('index.html', alertMsg='BT_ID and Password required')

    existing_user = users_collection.find_one({'btid': btid})

    if existing_user:
        return render_template('index.html', alertMsg='User already exists')

    users_collection.insert_one({'btid': btid, 'password': password})
    return render_template('chat.html', btid=btid)


# -------- CREATE ROOM -------- #
@app.route('/createroom', methods=['POST'])
def create_room():
    roomname = request.form.get('RoomName')
    password = request.form.get('password')

    if not roomname or not password:
        return render_template('index.html', alertMsg='Room name and password required')

    existing_room = rooms_collection.find_one({'roomname': roomname})

    if existing_room:
        return render_template('index.html', alertMsg='Room already exists')

    rooms_collection.insert_one({'roomname': roomname, 'password': password})

    chatList = list(chats_collection.find({'roomname': roomname}))
    return render_template('chat.html', roomname=roomname, myChatList=chatList) 


# -------- JOIN ROOM -------- #
@app.route('/joinchat', methods=['POST'])
def join_chat():
    roomname = request.form.get('roomname')
    password = request.form.get('password')

    room = rooms_collection.find_one({'roomname': roomname})

    if not room or room['password'] != password:
        return render_template('index.html', alertMsg='Invalid room or password')

    chatList = list(chats_collection.find({'roomname': roomname}))
    return render_template('chat.html', roomname=roomname, myChatList=chatList)


# -------- CREATE CHAT MESSAGE -------- #
@app.route('/createchat', methods=['POST'])
def create_chat_route():
    chat = request.form.get('chat')
    roomname = request.form.get('roomname')

    if chat and roomname:
        create_chat(roomname, chat)

    chatList = get_chat()
    myChatList = [item for item in chatList if item['roomname'] == roomname]

    return render_template('chat.html', roomname=roomname, myChatList=myChatList)


# -------- SHOW ROOMS -------- #
@app.route('/showroom', methods=['GET'])
def show_rooms():
    rooms = list(rooms_collection.find({}, {'_id': 0}))
    return render_template('rooms.html', rooms=rooms)


# -------- PWA FILES -------- #
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')


@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js')


# ---------------- DATABASE FUNCTIONS ---------------- #

def create_chat(roomname, chat):
    chat_data = {'roomname': roomname, 'chat': chat}
    result = chats_collection.insert_one(chat_data)
    return result.inserted_id


def get_chat():
    chats = chats_collection.find()
    return list(chats)


# ---------------- SOCKET.IO HANDLERS ---------------- #

@socketio.on('join')
def handle_join(data):
    room = data['room']
    username = data.get('username', 'User')

    join_room(room)
    send({'msg': f'{username} has joined the room.'}, room=room)


@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    username = data.get('username', 'User')

    leave_room(room)
    send({'msg': f'{username} has left the room.'}, room=room)


@socketio.on('message')
def handle_message(data):
    room = data['room']
    roomname = data['roomname']
    msg = data['msg']

    chat_data = {'roomname': roomname, 'chat': msg}
    chats_collection.insert_one(chat_data)

    send({'roomname': roomname, 'msg': msg}, room=room)


# ---------------- RUN APP ---------------- #

if __name__ == '__main__':
    socketio.run(app, debug=True)