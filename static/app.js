var app = angular.module('Shinobi', ['ngRoute']);

app.factory('notifyInterceptor', function($log) {
    var statusToType = function (status) {
        if (status / 100 === 2) {
            return 'success';
        } else {
            return 'danger';
        }
    };
    var showMessages = function (response) {
            if (response.data.hasOwnProperty('messages')) {
                response.data.messages.forEach(function (message) {
                    $('.notifications').notify({
                        message: { text: message },
                        type: statusToType(response.status),
                    }).show();
                });
            }
    };
    return {
        'response': function(response) {
            showMessages(response);
            return response;
        },
        'responseError': function(response) {
            showMessages(response);
            return response;
        },
    };
});

app.config(function($routeProvider, $httpProvider) {
    $routeProvider.
        when('/games', {
            templateUrl: 'partials/games.html',
            controller: 'GamesController'
        }).
        when('/games/:gid', {
            templateUrl: 'partials/game.html',
            controller: 'GameController'}).
        when('/games/:gid/lobby', {
            templateUrl: 'partials/game_lobby.html',
            controller: 'GameLobbyController'}).
        otherwise({
            redirectTo: '/games'
        });

    $httpProvider.interceptors.push('notifyInterceptor');
});
