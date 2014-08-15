from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView
import redis

app = Flask(__name__)

redis = redis.StrictRedis(decode_responses=True)

class GameList(MethodView):
    def get(self):
        gids = redis.lrange('games', 0, -1)
        games = []
        for gid in gids:
            name = redis.hget('games:{}'.format(gid), 'name')
            game = {'gid': gid, 'name': name}
            games.append(game)
        return jsonify({'games': games})

    def post(self):
        name = request.form['name']
        gid = redis.incr('games:next')
        redis.rpush('games', gid)
        redis.hset('games:{}'.format(gid), 'name', name)
        return redirect(url_for('game', gid=gid))

class Game(MethodView):
    def get(self, gid):
        name = redis.hget('games:{}'.format(gid), 'name')
        return jsonify({'gid': gid, 'name': name})

    def put(self, gid):
        pass

    def delete(self, gid):
        redis.lrem('games', 0, gid)
        redis.delete('games:{}'.format(gid))
        return ''

class PlayerList(MethodView):
    def get(self, gid):
        pids = redis.lrange('games:{}:players'.format(gid), 0, -1)
        players = [{'pid': pid} for pid in pids]
        return jsonify({'players': players})

    def post(self, gid):
        pid = redis.incr('games:{}:players:next'.format(gid))
        redis.rpush('games:{}:players'.format(gid), pid)
        return redirect(url_for('player', gid=gid, pid=pid))

class Player(MethodView):
    def get(self, gid, pid):
        cards = redis.hgetall('games:{}:players:{}:cards'.format(gid, pid))
        return jsonify({'gid': gid, 'pid': pid, 'cards': cards})

    def delete(self, gid, pid):
        redis.lrem('games:{}:players'.format(gid), 0, pid)
        redis.delete('games:{}:players:{}:cards'.format(gid, pid))
        return ''

class MoveList(MethodView):
    def post(self, gid, pid):
        move = request.get_json()
        valid, errors = validate_move(gid, pid, move)
        if valid:
            messages = execute_move(gid, pid, move)
            return jsonify({'messages': messages})
        else:
            return jsonify({'errors': errors})

def validate_move(gid, pid, move):
    return True, []

def execute_move(gid, pid, move):
    orders = (move['first'], move['second'], move['third'])
    messages = []
    for order in orders:
        messages.append(execute_order(gid, pid, order))
    return messages

def execute_order(gid, pid, order):
    if order:
        if order['type'] == 'deploy':
            return deploy(gid, pid, order['color'], order['to'])
        elif order['type'] == 'ninja':
            return ninja(gid, pid, order['color'], order['to'])
        elif order['type'] == 'transfer':
            return transfer(gid, pid, order['color'], order['from'], order['to'])
        elif order['type'] == 'attack':
            return attack(gid, pid, order['color'], order['to'])

def deploy(gid, pid, color, to_pid):
    redis.hincrby('games:{}:players:{}:hand'.format(gid, pid), color, -1)
    redis.hincrby('games:{}:players:{}:cards'.format(gid, to_pid), color, 1)
    return 'deployed {} to {}'.format(color, to_pid)

def ninja(gid, pid, color, to_pid):
    redis.hincrby('games:{}:players:{}:hand'.format(gid, pid), 'ninja', -1)
    redis.hincrby('games:{}:players:{}:cards'.format(gid, to_pid), color, -1)
    return 'killed {} in {}'.format(color, to_pid)

def tranfer(gid, pid, color, from_pid, to_pid):
    redis.hincrby('games:{}:players:{}:cards'.format(gid, from_pid), color, -1)
    redis.hincrby('games:{}:players:{}:cards'.format(gid, to_pid), color, 1)
    return 'transfered {} from {} to {}'.format(color, from_pid, to_pid)

def attack(gid, pid, color, to_pid):
    redis.hincrby('games:{}:players:{}:cards'.format(gid, to_pid), color, -1)
    return 'attacked {} in {}'.format(color, to_pid)

app.add_url_rule('/games', view_func=GameList.as_view('game_list'))
app.add_url_rule('/games/<int:gid>', view_func=Game.as_view('game'))
app.add_url_rule('/games/<int:gid>/players',
                 view_func=PlayerList.as_view('player_list'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>',
                 view_func=Player.as_view('player'))
app.add_url_rule('/games/<int:gid>/players/<int:pid>/moves',
                 view_func=MoveList.as_view('move_list'))

if __name__ == '__main__':
    app.run(debug=True)
