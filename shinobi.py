from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

games = []

class Game:
    def __init__(self, name):
        self.name = name
        self.players = []
        self.moves = []

class GameList(MethodView):
    def get(self):
        return jsonify({'games': [{'gid': gid, 'name': game[name]} for
                        gid, game in enumerate(games)]})

    def post(self):
        name = request.form['name']
        game = Game(name)
        games.append(game)
        gid = len(games) - 1
        return redirect(url_for('game', gid=gid))

class Game(MethodView):
    def get(self, gid):
        game = games[gid]
        return jsonify({'gid': gid, 'name': game[name]})

    def put(self, gid):
        pass

    def delete(self, gid):
        pass

app.add_url_rule('/games', view_func=GameList.as_view('game_list'))
app.add_url_rule('/games/<int:gid>', view_func=GameList.as_view('game'))

if __name__ == '__main__':
    app.run(debug=True)
