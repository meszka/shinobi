from flask import Flask, request, jsonify, redirect, url_for, Response
from flask.views import MethodView

from models import Game, Player

app = Flask(__name__)


def authenticate(auth):
    user = User(auth.username)
    if not user.check_password(auth.password):
        return None
    return user


def authorize(auth, user):
    current_user = authenticate(auth)
    return current_user.username == user.username


def auth_response():
    return Response(
            'Please log in', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})


class GameListView(MethodView):
    def get(self):
        gids = Game.get_gids()
        games = []
        for gid in gids:
            name = Game(gid).get_name()
            game = {'gid': gid, 'name': name}
            games.append(game)
        return jsonify({'games': games})

    def post(self):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        game_json = request.get_json()
        game = Game.create(user, game_json['name'])
        return redirect(url_for('game', gid=game.gid))

class GameView(MethodView):
    def get(self, gid):
        game = Game(gid)
        name = game.get_name()
        state = game.get_state()
        output = {
            'gid': gid,
            'name': name,
            'state': state,
        }
        if state == 'started':
            output['currentPlayer'] = game.get_current_pid()
        if state == 'ended':
            output['winners'] = game.get_winner_pids()
        return jsonify(output)

    def put(self, gid):
        game = Game(gid)
        if not authorize(request.authorization, game.owner):
            return auth_response()
        game_json = request.get_json()
        if game_json['state'] == 'started':
            game.start()
            return 'game started'

    def delete(self, gid):
        Game(gid).delete()
        return ''

class PlayerListView(MethodView):
    def get(self, gid):
        game = Game(gid)
        game_state = game.get_state()
        pids = game.get_pids()
        players = []
        for pid in pids:
            player = Player(gid, pid)
            cards = player.get_cards()
            player = {'pid': pid, 'cards': cards}
            if game_state == 'ended':
                player['color'] = player.get_color()
            players.append(player)
        return jsonify({'players': players})

    def post(self, gid):
        user = authenticate(request.authorization)
        if not user:
            return auth_response()
        player = Game(gid).create_player(user)
        return redirect(url_for('player', gid=gid, pid=player.pid))

class PlayerView(MethodView):
    def get(self, gid, pid):
        cards = Player(gid, pid).get_cards()
        return jsonify({'gid': gid, 'pid': pid, 'cards': cards})

    def delete(self, gid, pid):
        if not authorize(request.authorization, game.owner):
            return auth_response()
        Player(gid, pid).delete()
        return ''

class MoveListView(MethodView):
    def post(self, gid, pid):
        player = Player(gid, pid)
        user = player.get_user()
        if not authorize(request.authorization, user):
            return auth_response()
        move = request.get_json()
        valid, errors = player.validate_move(move)
        if valid:
            messages = player.execute_move(move)
            return jsonify({'status': 'success', 'messages': messages})
        else:
            return jsonify({'status': 'error', 'messages': errors})

class HandView(MethodView):
    def get(self, gid, pid):
        player = Player(gid, pid)
        user = player.get_user()
        if not authorize(request.authorization, user):
            return auth_response()
        hand =  player.get_hand()
        return jsonify({'hand': hand})

class NotificationView(MethodView):
    def get(self, gid):
        game = Game(gid)
        return Response(game.current_player_stream(),
                        mimetype='text/event-stream')


class UserListView(MethodView):
    def post(self):
        user_data = get_json()
        user = User.create(user_data['username'], user_data['password'])
        if not user:
            response_data = {status: 'error',
                             messages: 'Username already taken'}
            return jsonify(response_data), 400
        response_data = {'username': user.username, 'score:' user.get_score()}
        return Response(
                jsonify(response_data), 201,
                {'Location': url_for('user', username=user.username)})


class UserView(MethodView):
    def get(self, username):
        user = User(username)
        return jsonify({'username': user.username, 'score': user.get_score()})

    def put(self, username):
        user_data = get_json()
        user = User(username)
        if user_data.username != user.username:
            response_data = {status: 'error',
                             messages: 'Cannot change username'}
            return jsonify(response_data), 400
        user.set_password(user_data['password'])
        return '', 204


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
app.add_url_rule('/games/<int:gid>/notification',
                 view_func=NotificationView.as_view('notification'))
app.add_url_rule('/users/', view_func=UserListView.as_view('user_list'))
app.add_url_rule('/users/<str:username>', view_func=UserView.as_view('user'))

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
