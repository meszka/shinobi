var app = angular.module('Shinobi', ['ngRoute']);
app.config(function($routeProvider) {
    $routeProvider.
        when("/games", {
            templateUrl: "partials/games.html",
            controller: "GamesController"
        }).
        when("/games/:gid", {
            templateUrl: "partials/game.html",
            controller: "GameController"}).
        otherwise({
            redirectTo: '/games'
        });
});
