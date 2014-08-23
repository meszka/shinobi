var root = 'http://localhost:5000';

app.controller('GamesController', function ($scope, $http) {
    var update = function () {
        $http.get(root + '/games').success(function (data) {
            $scope.games = data.games;
        });
    };

    $scope.createGame = function (game) {
        $http.post(root + '/games', game);
        update();
    };

    update();
});

app.controller('GameController', function ($scope, $http, $routeParams) {
    var gid = $routeParams.gid;
    var myPid = 1;
    var pids;
    var selection = null;
    var move = {};

    var states = {};

    var switchState = function (state, options) {
        currentState = state;
        if (state.enter !== undefined) {
            state.enter(options);
        }
    };

    var addCard = function (player, card) {
        if (player.cards[card]) {
            player.cards[card]++;
        } else {
            player.cards[card] = 1;
        }
    };

    var removeCard = function (player, card) {
        player.cards[card]--;
    };

    states.test = {
        clickStack: function (player, card) {
            console.log('clicked stack: ' + player.pid + ' ' + card)
        },

        clickCard: function (card, index) {
            console.log('clicked card: ' + card + ' ' + index)
        },
    };

    states.first1 = {
        clickCard: function (card, index) {
            selection = { type: 'card', index: index }
            switchState(states.first2, { card: card });
        },
    };

    states.first2 = {
        enter: function (options) {
            this.card = options.card;
        },
        clickPlayer: function (player) {
            // TODO: ninja
            if (player.pid == myPid) {
                return;
            }
            selection = null;
            move.first = {
                type: 'deploy',
                to: player.pid,
                color: this.card,
            };
            var index = $scope.hand.indexOf(this.card);
            $scope.hand.splice(index, 1);
            addCard(player, this.card)
            console.log(move.first);
            switchState(states.second1);
        },
    };

    states.second1 = {
        clickCard: function (card, index) {
            move.second = {
                type: 'deploy',
                to: myPid,
                color: card,
            };
            console.log(move.second);
            $scope.hand.splice(index, 1);
            var myPlayer = _.find($scope.players, { pid: myPid });
            addCard(myPlayer, card);
            switchState(states.third);
        },
        clickStack: function (player, card) {
            if (player.pid == myPid) {
                return;
            }
            selection = { type: 'stack', pid: player.pid, card: card };
            switchState(states.second2, { player: player, card: card });
        }
    };

    states.second2 = {
        enter: function (options) {
            this.fromPlayer = options.player;
            this.card = options.card;
        },
        clickPlayer: function (player) {
            if (player.pid == myPid || player.pid == this.fromPlayer.pid) {
                return;
            }
            move.second = {
                type: 'transfer',
                from: this.fromPlayer.pid,
                to: player.pid,
                color: this.card,
            };
            console.log(move.second);
            selection = null;
            removeCard(this.fromPlayer, this.card);
            addCard(player, this.card);
            switchState(states.third);
        },
    };

    states.third = {
        clickStack: function (player, card) {
            if (player.pid == myPid) {
                return;
            }
            move.third = {
                type: 'attack',
                to: player.pid,
                color: card,
            };
            console.log(move.third);
            removeCard(player, card);
        },
    };

    var currentState = states.first1;

    $scope.range = _.range;

    $scope.clickStack = function (player, card) {
        // selection = { type: 'stack', pid: player.pid, card: card }
        if (currentState.clickStack !== undefined) {
            currentState.clickStack(player, card);
        }
    };

    $scope.clickCard = function (card, index) {
        // selection = { type: 'card', index: index }
        if (currentState.clickCard !== undefined) {
            currentState.clickCard(card, index);
        }
    };

    $scope.clickPlayer = function (player) {
        if (currentState.clickPlayer !== undefined) {
            currentState.clickPlayer(player);
        }
    };

    $scope.selectedStack = function (pid, card) {
        return selection &&
               selection.type == 'stack' &&
               selection.pid == pid &&
               selection.card == card;
    };

    $scope.selectedCard = function (index) {
        return selection &&
               selection.type == 'card' &&
               selection.index == index;
    };

    var update = function () {
        $http.get(root + '/games/' + gid).success(function (data) {
            $scope.game = data;
        });
        $http.get(root + '/games/' + gid + '/players').success(function (data) {
            $scope.players = data.players;
        });
        $http.get(root + '/games/' + gid + '/players/' + myPid + '/hand').
            success(function (data) {
                $scope.hand = data.hand;
            });
    };

    update();
});
