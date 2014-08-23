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

    $scope.range = function (n) {
       var range = [];
       for (var i = 0; i < n; i++) {
           range.push(i);
       }
       return range;
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
