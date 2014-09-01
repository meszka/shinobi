from flask import Flask, request, jsonify, redirect, url_for, Response
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
        game = Game(gid)
        name = game.get_name()
        status = game.get_state()
        current_player = game.get_current_pid()
        output = {
            'gid': gid,
            'name': name,
            'status': status,
            'currentPlayer': current_player,
        }
        if status == 'ended':
            output['winners'] = game.get_winner_pids()
        return jsonify(output)

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
        game_status = game.get_status()
        pids = game.get_pids()
        players = []
        for pid in pids:
            player = Player(gid, pid)
            cards = player.get_cards()
            player = {'pid': pid, 'cards': cards}
            if game_status == 'ended':
                player['color'] = player.get_color()
            players.append(player)
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
        player = Player(gid, pid)
        valid, errors = player.validate_move(move)
        if valid:
            messages = player.execute_move(move)
            return jsonify({'status': 'success', 'messages': messages})
        else:
            return jsonify({'status': 'error', 'messages': errors})

class HandView(MethodView):
    def get(self, gid, pid):
        player = Player(gid, pid)
        hand =  player.get_hand()
        return jsonify({'hand': hand})

class NotificationView(MethodView):
    def get(self, gid):
        game = Game(gid)
        return Response(game.current_player_stream(),
                        mimetype='text/event-stream')


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

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
