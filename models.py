import redis
import random

redis = redis.StrictRedis(decode_responses=True)

class Game:
    def __init__(self, gid):
        self.gid = gid

    def key(self, suffix=''):
        return 'games:{}{}'.format(self.gid, suffix)

    @staticmethod
    def get_gids():
        gids = redis.lrange('games', 0, -1)
        return [int(gid) for gid in gids]

    @staticmethod
    def create(name):
        gid = redis.incr('games:next')
        redis.rpush('games', gid)
        game = Game(gid)
        redis.hset(game.key(), 'name', name)
        return Game(gid)

    def delete(self):
        redis.lrem('games', 0, self.gid)
        redis.delete(self.key())

    def get_name(self):
        return redis.hget(self.key(), 'name')

    def get_current_pid(self):
        pid = redis.hget(self.key(), 'current_player')
        return int(pid)

    def set_current_pid(self, pid):
        redis.hset(self.key(), 'current_player', pid)

    def get_pids(self):
        pids = redis.lrange(self.key(':players'), 0, -1)
        return [int(pid) for pid in pids]

    def get_players(self):
        return [Player(self.gid, pid) for pid in self.get_pids()]

    def create_player(self):
        pid = redis.incr(self.key(':players:next'))
        redis.rpush(self.key(':players'), pid)

    def start(self):
        self.init_deck()
        colors = ['yellow', 'red', 'purple', 'green', 'blue']
        random.shuffle(colors)
        players = self.get_players()
        for player in players:
            player.set_color(colors.pop())
            player.draw_cards()
        current_player = random.pick(players)
        self.set_current_pid(current_player.pid)

    def next_player(self):
        current_pid = self.get_current_pid()
        pids = self.get_pids()
        current_index = pids.index(current_pid)
        next_index = (current_index + 1) % len(pids)
        next_pid = pids[next_index]
        self.set_current_pid(next_pid)

    def init_deck(self):
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
        cards = redis.hgetall(self.key(':cards'))
        for card, count in cards.items():
            cards[card] = int(count)
        return cards

    def get_hand(self):
        return redis.lrange(self.key(':hand'), 0, -1)

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
        self.draw_cards()
        Game(self.gid).next_player()
        # TODO: notify players waiting for move
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
        redis.lrem(self.key(':hand'), 1, color)
        redis.hincrby(to_player.key(':cards'), color, 1)
        return 'deployed {} to {}'.format(color, to_pid)

    def ninja(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.lrem(self.key(':hand'), 'ninja', 1)
        redis.hincrby(to_player.key(':cards'), color, -1)
        return 'killed {} in {}'.format(color, to_pid)

    def transfer(self, color, from_pid, to_pid):
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
