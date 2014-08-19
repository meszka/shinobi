app.controller('GamesController', function ($scope, $http) {
    var update = function () {
        $http.get('http://localhost:5000/games').success(function (data) {
                $scope.games = data.games;
            });
    };
    
    $scope.createGame = function (game) {
       $http.post('http://localhost:5000/games', game);
       update();
    };

    update();
});
