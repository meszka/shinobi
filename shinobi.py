from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView

from models import Game, Player

app = Flask(__name__)

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
        game_json = request.get_json()
        game = Game.create(game_json['name'])
        return redirect(url_for('game', gid=game.gid))

class GameView(MethodView):
    def get(self, gid):
        name = Game(gid).get_name()
        return jsonify({'gid': gid, 'name': name})

    def put(self, gid):
        game_json = request.get_json()
        if game_json['state'] == 'started':
            Game(gid).start()
            return 'game started'

    def delete(self, gid):
        Game(gid).delete()
        return ''

class PlayerListView(MethodView):
    def get(self, gid):
        game = Game(gid)
        pids = game.get_pids()
        players = [{'pid': pid} for pid in pids]
        return jsonify({'players': players})

    def post(self, gid):
        player = Game(gid).create_player()
        return redirect(url_for('player', gid=gid, pid=player.pid))

class PlayerView(MethodView):
    def get(self, gid, pid):
        cards = Player(gid, pid).get_cards()
        return jsonify({'gid': gid, 'pid': pid, 'cards': cards})

    def delete(self, gid, pid):
        Player(gid, pid).delete()
        return ''

class MoveListView(MethodView):
    def post(self, gid, pid):
        move = request.get_json()
        valid, errors = validate_move(gid, pid, move)
        if valid:
            messages = execute_move(gid, pid, move)
            return jsonify({'messages': messages})
        else:
            return jsonify({'errors': errors})

app.add_url_rule('/games', view_func=GameListView.as_view('game_list'))
app.add_url_rule('/games/<int:gid>', view_func=GameView.as_view('game'))
app.add_url_rule('/games/<int:gid>/players',
                 view_func=PlayerListView.as_view('player_list'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>',
                 view_func=PlayerView.as_view('player'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>/moves',
                 view_func=MoveListView.as_view('move_list'))

if __name__ == '__main__':
    app.run(debug=True)
