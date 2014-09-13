var root = 'http://localhost:5000';

app.controller('LoginController', function ($scope, $http) {
    $scope.logIn = function () {
        var auth = btoa($scope.user.username + ':' + $scope.user.password);
        $http.defaults.headers.common.Authorization = 'Basic ' + auth;
        $scope.username = $scope.user.username;
    };
    $scope.logOut = function () {
        $scope.username = undefined;
        $scope.user = {};
    };
    $scope.loggedIn = function () {
        return $scope.username !== undefined && $scope.username !== null;
    };
});

app.controller('GamesController', function ($scope, $http) {
    var update = function () {
        $http.get(root + '/games').success(function (data) {
            $scope.games = data.games;
        });
    };

    $scope.createGame = function (game) {
        $http.post(root + '/games', game).success(function () {
            update();
        });
    };

    update();
});

app.controller('GameLobbyController',
               function ($scope, $http, $routeParams, $location) {
    var gid = $routeParams.gid;

    var update = function () {
        $http.get(root + '/games/' + gid).success(function (data) {
            $scope.game = data;
        });
        $http.get(root + '/games/' + gid + '/players').
            success(function (data) {
                $scope.players = data.players;
            });
    };

    $scope.kick = function (player) {
        $http.delete(root + '/games/' + gid + '/players/' + player.pid);
        update();
    };

    $scope.join = function () {
        $http.post(root + '/games/' + gid + '/players');
        update();
    };

    $scope.start = function () {
        $http.put(root + '/games/' + gid, { state: 'started' });
        $location.path('/games/' + gid);
    };

    update();
});

app.controller('GameController',
               function ($scope, $http, $routeParams, $location) {
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
            if (card == 'ninja') {
                switchState(states.first2Ninja);
            } else {
                switchState(states.first2Deploy, { card: card });
            }
        },
    };

    states.first2Deploy = {
        enter: function (options) {
            this.card = options.card;
        },
        clickPlayer: function (player) {
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

    states.first2Ninja = {
        clickStack: function (player, card) {
            if (player.pid == myPid) {
                return;
            }
            selection = null;
            move.first = {
                type: 'ninja',
                to: player.pid,
                color: card,
            };
            var index = $scope.hand.indexOf('ninja');
            $scope.hand.splice(index, 1);
            removeCard(player, card)
            console.log(move.first);
            switchState(states.second1);
        },
    };

    states.second1 = {
        clickCard: function (card, index) {
            if (card == 'ninja') {
                return;
            }
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
            console.log(move);
            removeCard(player, card);
            switchState(states.disabled);
        },
        clickNoAttack: function () {
            move.third = null;
            console.log(move);
            switchState(states.disabled);
        },
    };

    states.disabled = {};

    var currentState = states.first1;

    $scope.messages = []

    $scope.range = _.range;

    $scope.clickStack = function (player, card) {
        if (currentState.clickStack !== undefined) {
            currentState.clickStack(player, card);
        }
    };

    $scope.clickCard = function (card, index) {
        if (currentState.clickCard !== undefined) {
            currentState.clickCard(card, index);
        }
    };

    $scope.clickNoAttack = function () {
        if (currentState.clickNoAttack !== undefined) {
            currentState.clickNoAttack();
        }
    };

    $scope.showNoAttack = function () {
        return currentState === states.third;
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

    $scope.clickDone = function () {
        switchState(states.disabled);
        $http.post(root + '/games/' + gid + '/players/' + myPid + '/moves', move).
            success(function (data) {
                console.log(data);
                $scope.messages = data.messages;
                update();
                switchState(states.first1);
                move = {};
            });
    };

    $scope.showDone = function () {
        return move.hasOwnProperty('first') &&
               move.hasOwnProperty('second') &&
               move.hasOwnProperty('third');
    };

    $scope.clickReset = function () {
        move = {};
        update();
        switchState(states.first1);
    };

    var update = function () {
        $http.get(root + '/games/' + gid).success(function (data) {
            $scope.game = data;
            if ($scope.game.state == 'setup') {
                $location.path($location.path() + '/lobby');
            }
            myPid = data.currentPlayer;
            $http.get(root + '/games/' + gid + '/players/' + myPid + '/hand').
                success(function (data) {
                    $scope.hand = data.hand;
                });
        });
        $http.get(root + '/games/' + gid + '/players').success(function (data) {
            $scope.players = data.players;
        });
    };

    update();
});
