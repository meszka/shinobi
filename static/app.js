var app = angular.module('Shinobi', ['ngRoute', 'ngCookies']);

app.factory('notifyInterceptor', function($q) {
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
                    if (!message) {
                        return;
                    }
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
            return $q.reject(response);
        },
    };
});


app.factory('authInterceptor', function($q) {
    return {
        'responseError': function(response) {
            if (response.status === 401) {
                $('.notifications').notify({
                    message: { text: 'Please log in' },
                    type: 'warning',
                }).show();
            }
            $q.reject(response);
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
            controller: 'GameController'
        }).
        when('/games/:gid/lobby', {
            templateUrl: 'partials/game_lobby.html',
            controller: 'GameLobbyController'
        }).
        when('/users', {
            templateUrl: 'partials/users.html',
            controller: 'UsersController'
        }).
        otherwise({
            redirectTo: '/games'
        });
    $httpProvider.defaults.headers.
        common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.interceptors.push('authInterceptor');
    $httpProvider.interceptors.push('notifyInterceptor');
});
