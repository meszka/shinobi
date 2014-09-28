app.controller('LoginController', function ($scope, $http, $rootScope) {
    $scope.logIn = function () {
        var auth = btoa($scope.user.username + ':' + $scope.user.password);
        $http.defaults.headers.common.Authorization = 'Basic ' + auth;
        $rootScope.username = $scope.user.username;
        $rootScope.$broadcast('updateEvent');
    };
    $scope.logOut = function () {
        $rootScope.username = undefined;
        $scope.user = {};
    };
    $scope.loggedIn = function () {
        return $rootScope.username !== undefined &&
               $rootScope.username !== null;
    };
    $scope.create = function () {
        $http.post('/users', $scope.user).success(function () {
            $scope.logIn();
        });
    };
});

app.controller('UsersController', function ($scope, $http) {
    $http.get('/users').success(function (data) {
        $scope.users = data.users;
    });
});

app.controller('GamesController', function ($scope, $http) {
    var update = function () {
        $http.get('/games').success(function (data) {
            $scope.games = data.games;
        });
    };

    $scope.createGame = function (game) {
        $http.post('/games', game).success(update);
    };

    update();
});

app.controller('GameLobbyController',
               function ($scope, $http, $routeParams, $location, $rootScope) {
    var gid = $routeParams.gid;
    var events = new EventSource('/games/' + gid + '/events');
    var myPid = null;

    var update = function () {
        $http.get('/games/' + gid).success(function (data) {
            $scope.game = data;
        });
        $http.get('/games/' + gid + '/players').
            success(function (data) {
                $scope.players = data.players;
                data.players.forEach(function (player) {
                    if (player.username === $rootScope.username) {
                        myPid = player.pid;
                        $scope.joined = true;
                    }
                });
            });
    };

    $scope.joined = false;

    $scope.isOwner = function () {
        if (!$scope.game) {
            return false;
        }
        return $scope.game.owner === $rootScope.username;
    };

    $scope.kick = function (player) {
        $http.delete('/games/' + gid + '/players/' + player.pid).
            success(update);
    };

    $scope.join = function () {
        $http.post('/games/' + gid + '/players').success(function (data) {
            myPid = data.pid;
            $scope.joined = true;
            update();
        });
    };

    $scope.leave = function () {
        $http.delete('/games/' + gid + '/players/' + myPid).
            success(function () {
                myPid = null;
                $scope.joined = false;
                update();
            });
    };

    $scope.start = function () {
        $http.put('/games/' + gid, { state: 'started' }).success(function () {
            $location.path('/games/' + gid);
        });
    };

    events.addEventListener('players', update);
    events.addEventListener('state', function (event) {
        if (event.data === 'started') {
            $rootScope.$apply(function () {
                $location.path('/games/' + gid);
            });
        }
    });

    $scope.$on('updateEvent', update);

    update();
});

app.controller('GameController',
               function ($scope, $http, $routeParams, $location, $rootScope) {
    var gid = $routeParams.gid;
    var myPid;
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
            if (player.pid === myPid) {
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
            if (player.pid === this.fromPlayer.pid) {
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

    var currentState = states.disabled;

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
        $http.post('/games/' + gid + '/players/' + myPid + '/moves', move).
            success(function (data) {
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

    $scope.myTurn = function () {
        return $scope.game && myPid === $scope.game.currentPlayer;
    };

    // TODO: break into init and update (?)
    var update = function () {
        $http.get('/games/' + gid).success(function (data) {
            $scope.game = data;
            if ($scope.game.state == 'setup') {
                $location.path($location.path() + '/lobby');
            }
            $http.get('/games/' + gid + '/players').success(function (data) {
                $scope.players = data.players;
                data.players.forEach(function (player) {
                    if (player.username === $rootScope.username) {
                        myPid = player.pid;
                        $scope.myPid = player.pid;
                        $scope.myColor = player.color;
                        console.log("I'm player " +  myPid);
                    }
                    if (myPid === $scope.game.currentPlayer) {
                        switchState(states.first1);
                    }
                });
                if (myPid !== undefined) {
                    $http.get('/games/' + gid + '/players/' + myPid + '/hand').
                        success(function (data) {
                            data.hand.sort();
                            $scope.hand = data.hand;
                        });
                }
            });
        });
    };
    $scope.update = update;

    update();

    $scope.$on('updateEvent', function (event, args) {
        update();
    });

    var source = new EventSource('/games/' + gid + '/events');
    source.addEventListener('current_player', update);
});
