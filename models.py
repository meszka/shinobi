import os
import random
import collections
import itertools
import json
import redis
from werkzeug.security import generate_password_hash, check_password_hash


REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')

redis = redis.StrictRedis(host=REDIS_HOST, decode_responses=True)


def best(scores):
    max_score = max([score for player, score in scores])
    return [player for player, score in scores if score == max_score]


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
    def get_all():
        return [Game(gid) for gid in Game.get_gids()]

    @staticmethod
    def create(owner, name):
        gid = redis.incr('games:next')
        redis.rpush('games', gid)
        game = Game(gid)
        redis.hset(game.key(), 'owner', owner.username)
        redis.hset(game.key(), 'name', name)
        redis.hset(game.key(), 'state', 'setup')
        return Game(gid)

    def exists(self):
        return self.get_name() is not None

    def delete(self):
        redis.lrem('games', 0, self.gid)
        redis.delete(self.key())

    def get_name(self):
        return redis.hget(self.key(), 'name')

    def set_name(self, name):
        redis.hset(game.key(), 'name', name)

    def get_owner_username(self):
        return redis.hget(self.key(), 'owner')

    def get_owner(self):
        return User(self.get_owner_username())

    def get_state(self):
        return redis.hget(self.key(), 'state')

    def set_state(self, state):
        redis.hset(self.key(), 'state', state)
        redis.publish(self.key(':state_channel'), state)

    def get_last_pid(self):
        pid = redis.hget(self.key(), 'last_player')
        if pid:
            return int(pid)

    def set_last_pid(self, pid):
        redis.hset(self.key(), 'last_player', pid)

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

    def get_winner_pids(self):
        pids = redis.lrange(self.key(':winners'), 0, -1)
        return [int(pid) for pid in pids]

    def set_winner_pids(self, pids):
        for pid in pids:
            redis.rpush(self.key(':winners'), pid)

    def deck_empty(self):
        deck_length = int(redis.llen(self.key(':deck')))
        return deck_length == 0

    def create_player(self, user):
        pid = redis.incr(self.key(':players:next'))
        player = Player(self.gid, pid)
        player.set_username(user.username)
        redis.rpush(self.key(':players'), pid)
        event_data = json.dumps({'action': 'join', 'player': pid})
        redis.publish(self.key(':players_channel'), event_data)
        return player

    def get_data(self):
        return {
            'gid': self.gid,
            'name': self.get_name(),
            'state': self.get_state(),
            'owner': self.get_owner_username(),
        }

    def start(self):
        self.init_deck()
        colors = ['yellow', 'red', 'purple', 'green', 'blue']
        random.shuffle(colors)
        players = self.get_players()
        for player in players:
            player.set_color(colors.pop())
            player.draw_cards()
        current_player = random.choice(players)
        self.set_current_pid(current_player.pid)
        self.set_state('started')

    def next_player(self):
        current_pid = self.get_current_pid()
        pids = self.get_pids()
        current_index = pids.index(current_pid)
        next_index = (current_index + 1) % len(pids)
        next_pid = pids[next_index]
        self.set_current_pid(next_pid)
        redis.publish(self.key(':current_player_channel'), next_pid)

    def end(self):
        winners = self.find_winners()
        for player in winners:
            player.get_user().increment_score()
        winner_pids = [player.pid for player in winners]
        self.set_winner_pids(winner_pids)
        self.set_state('ended')

    def find_winners(self):
        players = self.get_players()
        color_counts = collections.Counter()
        for player in players:
            for color, count in player.get_cards().items():
                color_counts[color] += count

        player_colors = [player.get_color() for player in players]
        for color in color_counts:
            if color not in player_colors:
                color_counts[color] = 0

        winning_colors = best(color_counts.items())
        colors_to_players = {player.get_color(): player for player in players}
        winners = [colors_to_players[color] for color in winning_colors]

        if len(winners) == 1:
            return winners
        else:
            def score2(player):
                return player.cards.get(player.get_color(), 0)
            winners2 = [(score2(player), player) for player in winners]
            return best(winners2)

    def init_deck(self):
        deck = 11 * ['yellow', 'red', 'purple', 'green', 'blue'] + 3 * ['ninja']
        random.shuffle(deck)
        for card in deck:
            redis.rpush(self.key(':deck'), card)

    def event_stream(self):
        event_names = {
            self.key(':current_player_channel'): 'current_player',
            self.key(':state_channel'): 'state',
            self.key(':players_channel'): 'players',
        }
        p = redis.pubsub()
        p.subscribe(event_names)
        for message in p.listen():
            if message['type'] == 'message':
                data = message['data']
                channel = message['channel']
                event = event_names[channel]
                yield 'event: {}\ndata: {}\n\n'.format(event, data)


class Player:
    def __init__(self, gid, pid):
        self.gid = gid
        self.pid = pid

    def key(self, suffix=''):
        return 'games:{}:players:{}{}'.format(self.gid, self.pid, suffix)

    def get_username(self):
        return redis.hget(self.key(), 'user')

    def set_username(self, username):
        redis.hset(self.key(), 'user', username)

    def get_user(self):
        return User(self.get_username())

    def get_cards(self):
        cards = redis.hgetall(self.key(':cards'))
        for card, count in cards.items():
            cards[card] = int(count)
        return cards

    def get_hand(self):
        return redis.lrange(self.key(':hand'), 0, -1)

    def get_data(self):
        return {
            'gid': self.gid,
            'pid': self.pid,
            'username': self.get_username(),
            'cards': self.get_cards()
        }

    def exists(self):
        return self.get_username() is not None

    def delete(self):
        game = Game(self.gid)
        redis.lrem(game.key(':players'), 0, self.pid)
        redis.delete(self.key(':cards'))
        redis.delete(self.key(':hand'))
        event_data = json.dumps({'action': 'leave', 'player': self.pid})
        redis.publish(game.key(':players_channel'), event_data)

    def validate_move(self, move):
        self.validation_setup()
        all_orders = 'first' in move and 'second' in move and 'third' in move
        if not all_orders:
            return False, ['Incomplete move']
        results = [
            self.validate_first(move['first']),
            self.validate_second(move['second']),
            self.validate_third(move['third']),
        ]
        oks, messages = zip(*results)
        return all(oks), list(itertools.chain(messages))

    def validation_setup(self):
        self.dirty = set()
        self.tmp_hand = self.get_hand()
        self.tmp_cards = {}
        for player in Game(self.gid).get_players():
            dd = collections.defaultdict(int, player.get_cards())
            self.tmp_cards[player.pid] = dd

    def validate_first(self, order):
        if 'type' not in order:
            return False, 'No type for first order'
        if order['type'] == 'deploy':
            return self.validate_first_deploy(order)
        if order['type'] == 'ninja':
            return self.validate_ninja(order)
        return False, 'Wrong type for first order'

    def validate_second(self, order):
        if 'type' not in order:
            return False, 'No type for second order'
        if order['type'] == 'deploy':
            return self.validate_second_deploy(order)
        if order['type'] == 'transfer':
            return self.validate_transfer(order)
        return False, 'Wrong type for second order'

    def validate_third(self, order):
        if order is None:
            return self.validate_no_attack()
        if 'type' not in order:
            return False, 'No type for third order'
        if order['type'] == 'attack':
            return self.validate_attack(order)
        return False, 'Wrong type for third order'

    def validate_first_deploy(self, order):
        to_pid = order['to']
        color = order['color']
        if color not in self.tmp_hand:
            return False, 'You do not have a {} card to deploy' \
                          .format(color)
        if to_pid == self.pid:
            return False, 'You cannot deploy to your own ' \
                          'province in the first order'
        self.tmp_hand.remove(color)
        self.tmp_cards[to_pid][color] += 1
        self.dirty.add((to_pid, color))
        return True, ''

    def validate_second_deploy(self, order):
        to_pid = order['to']
        color = order['color']
        if color not in self.tmp_hand:
            return False, 'You do not have a {} card to deploy' \
                          .format(color)
        if to_pid != self.pid:
            return False, "You cannot deploy to an enemy's" \
                          "province in the second order"
        self.tmp_hand.remove(color)
        self.tmp_cards[to_pid][color] += 1
        return True, ''

    def validate_ninja(self, order):
        to_pid = order['to']
        color = order['color']
        if 'ninja' not in self.tmp_hand:
            return False, 'You do not have a ninja card'
        if color not in self.tmp_cards[to_pid]:
            to_username = Player(self.gid, to_pid).get_username()
            return False, '{} does not have a {} card' \
                          .format(to_username, color)
        self.tmp_hand.remove('ninja')
        self.tmp_cards[to_pid][color] -= 1
        return True, ''

    def validate_transfer(self, order):
        from_pid = order['from']
        to_pid = order['to']
        color = order['color']
        if from_pid == self.pid:
            return False, 'You cannot transfer from your own province'
        if self.tmp_cards[from_pid][color] == 0:
            from_username = Player(self.gid, from_pid).get_username()
            return False, '{} does not have a {} card' \
                          .format(from_username, color)
        self.tmp_cards[from_pid][color] -= 1
        self.tmp_cards[to_pid][color] += 1
        return True, ''

    def validate_attack(self, order):
        to_pid = order['to']
        color = order['color']
        if self.can_attack(to_pid, color):
            return True, ''
        else:
            to_username = Player(self.gid, to_pid).get_username()
            return False, 'You cannot attack {} {}' \
                          .format(to_username, color)

    def validate_no_attack(self):
        if all(not self.can_attack(pid, color)
               for pid, color in self.enemy_stacks()):
            return True, ''
        else:
            return False, 'You must attack if you can'

    def enemy_stacks(self):
        enemies = Game(self.gid).get_pids()
        enemies.remove(self.pid)
        for pid in enemies:
            for color, count in self.tmp_cards[pid].items():
                if count > 0:
                    yield (pid, color)

    def can_attack(self, enemy_pid, enemy_color):
        if (enemy_pid, enemy_color) in self.dirty:
            return False
        enemy_count = self.tmp_cards[enemy_pid][enemy_color]
        my_cards = self.tmp_cards[self.pid]
        return any(color for color, count in my_cards.items()
                   if count > enemy_count and color != enemy_color)

    def execute_move(self, move):
        orders = (move['first'], move['second'], move['third'])
        messages = []
        for order in orders:
            messages.append(self.execute_order(order))
        self.draw_cards()
        game = Game(self.gid)
        last_pid = game.get_last_pid()
        if not last_pid and game.deck_empty():
            game.set_last_pid(self.pid)
        if self.pid == last_pid:
            game.end()
        else:
            game.next_player()
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
        to_username = to_player.get_username()
        return 'deployed {} to {}'.format(color, to_username)

    def ninja(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.lrem(self.key(':hand'), 1, 'ninja')
        redis.hincrby(to_player.key(':cards'), color, -1)
        to_username = to_player.get_username()
        return "killed {} in {}'s province".format(color, to_username)

    def transfer(self, color, from_pid, to_pid):
        from_player = Player(self.gid, from_pid)
        to_player = Player(self.gid, to_pid)
        redis.hincrby(from_player.key(':cards'), color, -1)
        redis.hincrby(to_player.key(':cards'), color, 1)
        from_username = from_player.get_username()
        to_username = to_player.get_username()
        return 'transfered {} from {} to {}' \
               .format(color, from_username, to_username)

    def attack(self, color, to_pid):
        to_player = Player(self.gid, to_pid)
        redis.hincrby(to_player.key(':cards'), color, -1)
        to_username = to_player.get_username()
        return "attacked {} in {}'s province".format(color, to_username)

    def get_color(self):
        return redis.hget(self.key(), 'color')

    def set_color(self, color):
        redis.hset(self.key(), 'color', color)

    def draw_cards(self):
        hand_length = redis.llen(self.key(':hand'))
        for i in range(4 - hand_length):
            card = redis.lpop('games:{}:deck'.format(self.gid))
            if card:
                redis.rpush(self.key(':hand'), card)


class User:
    def __init__(self, username):
        self.username = username

    def key(self, suffix=''):
        return 'users:{}{}'.format(self.username, suffix)

    @staticmethod
    def create(username, password):
        user = User(username)
        pw_hash = generate_password_hash(password)
        ok = redis.hsetnx(user.key(), 'password_hash', pw_hash)
        if not ok:
            return False
        redis.hset('users:{}'.format(username), 'score', 0)
        redis.rpush('users', username)
        return user

    @staticmethod
    def get_usernames():
        return redis.lrange('users', 0, -1)

    @staticmethod
    def get_all():
        return [User(username) for username in User.get_usernames()]

    def exists(self):
        return redis.hget(self.key(), 'password_hash') is not None

    def delete(self):
        redis.delete(self.key())
        redis.lrem('users', 0, self.username)

    def check_password(self, password):
        pw_hash = redis.hget(self.key(), 'password_hash')
        if not pw_hash:
            return False
        return check_password_hash(pw_hash, password)

    def set_password(self, password):
        pw_hash = generate_password_hash(password)
        return redis.hset(self.key(), 'password_hash', pw_hash)

    def get_score(self):
        return int(redis.hget(self.key(), 'score'))

    def increment_score(self, amount=1):
        redis.hincrby(self.key(), 'score', amount)

    def get_data(self):
        return {'username': self.username, 'score': self.get_score()}
