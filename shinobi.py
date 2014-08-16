from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView
import redis
import random

app = Flask(__name__)

redis = redis.StrictRedis(decode_responses=True)

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

class Game:
    def __init__(self, gid):
        self.gid = gid

    def key(self, suffix=''):
        return 'games:{}}{}'.format(self.gid, suffix)

    @staticmethod
    def get_gids():
        return redis.lrange('games', 0, -1)

    @staticmethod
    def create(name):
        gid = redis.incr('games:next')
        redis.rpush('games', gid)
        redis.hset(self.key(), 'name', name)
        return Game(gid)

    def delete(self):
        redis.lrem('games', 0, gid)
        redis.delete(self.key())

    def get_name(self):
        redis.hget(self.key(), 'name')

    def get_pids(self):
        return redis.lrange(self.key(':players'), 0, -1)

    def get_players(self):
        return [Player(self.gid, pid) for pid in self.get_pids]

    def create_player(self):
        pid = redis.incr(self.key(':players:next'))
        redis.rpush(self.key(':players'), pid)

    def start(self):
        self.init_deck()
        colors = ['yellow', 'red', 'purple', 'green', 'blue']
        random.shuffle(colors)
        for player in self.get_players():
            player.set_color(colors.pop())
            player.draw_cards()

    def init_deck(gid):
        deck = 11 * ['yellow', 'red', 'purple', 'green', 'blue'] + 3 * ['ninja']
        random.shuffle(deck)
        for card in deck:
            redis.rpush(self.key(':deck'), card)


class Player:
    def __init__(self, gid, pid):
        self.gid = gid
        self.pid = pid

    def key(self, suffix=''):
        return 'games:{}:players:{}{}'.format(self.gid, self.pid, suffix)

    def get_cards(self):
        return redis.hgetall(self.key(':cards'))

    def delete(self):
        game = Game(self.gid)
        redis.lrem(game.key(':players'), 0, self.pid)
        redis.delete(self.key(':cards'))
        redis.delete(self.key(':hand'))

    def validate_move(self, move):
        return True, []

    def execute_move(self, move):
        orders = (move['first'], move['second'], move['third'])
        messages = []
        for order in orders:
            messages.append(self.execute_order(order))
        return messages

    def execute_order(self, order):
        if order:
            if order['type'] == 'deploy':
                return self.deploy(order['color'], order['to'])
            elif order['type'] == 'ninja':
                return self.ninja(order['color'], order['to'])
            elif order['type'] == 'transfer':
                return self.transfer(order['color'], order['from'], order['to'])
            elif order['type'] == 'attack':
                return self.attack(order['color'], order['to'])

    def deploy(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.lrem(self.key(':hand'), color, 1)
        redis.hincrby(to_player.key(':cards'), color, 1)
        return 'deployed {} to {}'.format(color, to_pid)

    def ninja(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.lrem(self.key(':hand'), 'ninja', 1)
        redis.hincrby(to_player.key(':cards'), color, -1)
        return 'killed {} in {}'.format(color, to_pid)

    def tranfer(self, color, from_pid, to_pid):
        from_player = Player(self.gid, from_pid)
        to_player = Player(self.gid, to_pid)
        redis.hincrby(from_player.key(':cards'), color, -1)
        redis.hincrby(to_player.key(':cards'), color, 1)
        return 'transfered {} from {} to {}'.format(color, from_pid, to_pid)

    def attack(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.hincrby(to_player.key(':cards'), color, -1)
        return 'attacked {} in {}'.format(color, to_pid)

    def set_color(self, color):
        redis.hset(self.key(), 'color', color)

    def draw_cards(self):
        hand_length = redis.llen(self.key(':hand'))
        for i in range(4 - hand_length):
            card = redis.lpop('games:{}:deck'.format(self.gid))
            redis.rpush(self.key(':hand'), card)

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
