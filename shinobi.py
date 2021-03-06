import os
from flask import request, jsonify, redirect, url_for, Response
from flask.views import MethodView

from make_json_app import make_json_app
from models import Game, Player, User

app = make_json_app(__name__)

app.config['DEBUG'] = bool(os.getenv('DEBUG', False))
app.config['HOST'] = os.getenv('HOST', '127.0.0.1')

def authenticate(auth):
    if not auth:
        return None
    user = User(auth.username)
    if not user.check_password(auth.password):
        return None
    return user


def authorize(auth, user):
    current_user = authenticate(auth)
    if not current_user:
        return None
    return current_user.username == user.username


def auth_response():
    auth_type = 'Basic'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        auth_type = 'xBasic'
    headers = {'WWW-Authenticate':
               '{} realm="Login Required"'.format(auth_type)}
    return 'Please log in', 401, headers


class GameListView(MethodView):
    def get(self):
        games = Game.get_all()
        games_data = [game.get_data() for game in games]
        return jsonify({'games': games_data})

    def post(self):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        game_json = request.get_json()
        game = Game.create(user, game_json['name'])
        response_data = game.get_data()
        return (jsonify(response_data), 201,
                {'Location': url_for('game', gid=game.gid)})


class GameView(MethodView):
    def get(self, gid):
        game = Game(gid)
        if not game.exists():
            return '', 404
        game_data = game.get_data()
        last_pid = game.get_last_pid()
        if last_pid:
            game_data['lastPlayer'] = last_pid
        if game_data['state'] == 'started':
            game_data['currentPlayer'] = game.get_current_pid()
        if game_data['state'] == 'ended':
            game_data['winners'] = game.get_winner_pids()
        return jsonify(game_data)

    def put(self, gid):
        game = Game(gid)
        owner = game.get_owner()
        state = game.get_state()
        errors = []
        if not authorize(request.authorization, owner):
            return auth_response()
        game_json = request.get_json()
        if game_json['gid'] != gid:
            errors.append('Cannot modify gid')
        if game_json['owner'] != owner.username:
            errors.append('Cannot modify owner')
        if game_json['state'] != state:
            if game_json['state'] != 'started':
                errors.append('Cannot change state to {}' \
                              .format(game_json['state']))
            if state != 'setup':
                errors.append('Game must be in setup state')
            if len(game.get_pids()) < 3:
                response_data = {'messages':
                                 ['Game must have at least 3 players']}
        if errors:
            return jsonify({'messages': errors}), 400
        if game_json['state'] == 'started' and state != 'started':
            game.start()
        game.set_name(game_json['name'])
        return '', 204

    def delete(self, gid):
        game = Game(gid)
        owner = game.get_owner()
        if not authorize(request.authorization, owner):
            return auth_response()
        Game(gid).delete()
        return '', 204


class PlayerListView(MethodView):
    def get(self, gid):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        game = Game(gid)
        game_state = game.get_state()
        pids = game.get_pids()
        players = []
        for pid in pids:
            player = Player(gid, pid)
            cards = player.get_cards()
            username = player.get_username()
            player_data = player.get_data()
            if (user and username == user.username) or game_state == 'ended':
                player_data['color'] = player.get_color()
            players.append(player_data)
        return jsonify({'players': players})

    def post(self, gid):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        game = Game(gid)
        players = game.get_players()
        if len(players) >= 5:
            response_data = {
                'messages': ['There cannot be more than 5 players in a game']
            }
            return jsonify(response_data), 400
        if any([p for p in players if p.get_username() == user.username]):
            response_data = {
                'messages': ['You are already in this game']
            }
            return jsonify(response_data), 400
        player = game.create_player(user)
        response_data = player.get_data()
        return (jsonify(response_data), 201,
                {'Location': url_for('player', gid=gid, pid=player.pid)})


class PlayerView(MethodView):
    def get(self, gid, pid):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        player = Player(gid, pid)
        if not player.exists():
            return '', 404
        cards = player.get_cards()
        response_data = player.get_data()
        if user.username == player.get_username():
            response_data['color'] = player.get_color()
        return jsonify(response_data)

    def delete(self, gid, pid):
        game = Game(gid)
        owner = game.get_owner()
        player = Player(gid, pid)
        user = player.get_user()
        auth = request.authorization
        if not (authorize(auth, owner) or authorize(auth, user)):
            return auth_response()
        Player(gid, pid).delete()
        return '', 204


class MoveListView(MethodView):
    def post(self, gid, pid):
        game = Game(gid)
        state = game.get_state()
        if state == 'setup':
            return jsonify({'messages': ["The game hasn't started yet"]}), 400
        if state == 'ended':
            return jsonify({'messages': ['The game has ended']}), 400
        if not game.get_current_pid() == pid:
            return jsonify({'messages': ['It is not your turn']}), 400
        player = Player(gid, pid)
        user = player.get_user()
        if not authorize(request.authorization, user):
            return auth_response()
        move = request.get_json()
        valid, errors = player.validate_move(move)
        if valid:
            messages = player.execute_move(move)
            return jsonify({'messages': messages})
        else:
            return jsonify({'messages': errors}), 400


class HandView(MethodView):
    def get(self, gid, pid):
        player = Player(gid, pid)
        user = player.get_user()
        if not authorize(request.authorization, user):
            return auth_response()
        hand =  player.get_hand()
        return jsonify({'hand': hand})


class EventsView(MethodView):
    def get(self, gid):
        game = Game(gid)
        return Response(game.event_stream(),
                        mimetype='text/event-stream')


class UserListView(MethodView):
    def get(self):
        users = User.get_all()
        users_data = [user.get_data() for user in users]
        return jsonify({'users': users_data})

    def post(self):
        user_data = request.get_json()
        user = User.create(user_data['username'], user_data['password'])
        if not user:
            response_data = {'messages': ['Username already taken']}
            return jsonify(response_data), 400
        response_data = user.get_data()
        return (jsonify(response_data), 201,
                {'Location': url_for('user', username=user.username)})


class UserView(MethodView):
    def get(self, username):
        user = User(username)
        if not user.exists():
            return '', 404
        return jsonify(user.get_data())

    def put(self, username):
        user = User(username)
        if not user.exists():
            return '', 404
        if not authorize(request.authorization, user):
            return auth_response()
        user_data = get_json()
        if user_data['username'] != user.username:
            response_data = {'messages': ['Cannot change username']}
            return jsonify(response_data), 400
        if user_data['score'] != user.get_score():
            response_data = {'messages': ['Cannot change score']}
            return jsonify(response_data), 400
        user.set_password(user_data['password'])
        return '', 204


@app.route('/')
def index():
    return redirect('/static/index.html')


app.add_url_rule('/games', view_func=GameListView.as_view('game_list'))
app.add_url_rule('/games/<int:gid>', view_func=GameView.as_view('game'))
app.add_url_rule('/games/<int:gid>/players',
                 view_func=PlayerListView.as_view('player_list'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>',
                 view_func=PlayerView.as_view('player'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>/moves',
                 view_func=MoveListView.as_view('move_list'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>/hand',
                 view_func=HandView.as_view('hand'))
app.add_url_rule('/games/<int:gid>/events',
                 view_func=EventsView.as_view('events'))
app.add_url_rule('/users', view_func=UserListView.as_view('user_list'))
app.add_url_rule('/users/<username>', view_func=UserView.as_view('user'))

if __name__ == '__main__':
    app.run(host=app.config['HOST'], threaded=True)
