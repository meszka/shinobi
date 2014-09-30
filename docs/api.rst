REST API
========

Overview
--------

================================ === ==== === ======
URI                              GET POST PUT DELETE
================================ === ==== === ======
/games                           X   X
/games/{gid}                     X        X   X
/games/{gid}/players             X   X
/games/{gid}/players/{pid}       X            X
/games/{gid}/players/{pid}/hand  X
/games/{gid}/players/{pid}/moves *   X
/games/{gid}/events              X
/users                           X   X
/users/{username}                X        *   *
================================ === ==== === ======

Request and response entities are in the JSON format (Content-Type:
application/json).

Some requests require HTTP basic authentication with a username and password of
a user (created with POST /users).

GET /games
----------

Response
^^^^^^^^

The list of games::

    {
        "games": [
            {
                "gid": 1,
                "name": "game 1",
                "state": "setup",
                "owner": "alice",
            },
            {
                "gid": 1,
                "name": "game 2",
                "state": "started",
                "owner": "bob",
            }
        ]
    }

Status: 200

POST /games
-----------

Creates a new game.

Request
^^^^^^^

A game object with a name::

    { "name": "my game" }

Response
^^^^^^^^

The new game::

    {
        "gid": 5,
        "name": "my game",
        "state": "setup",
        "owner": "joe",
    }

Status: 201

Headers: Location with URI of new game.

GET /games/{gid}
----------------

Response
^^^^^^^^

If the game {gid} exists:

Data of game::

    {
        "gid": 5,
        "name": "my game",
        "state": "setup",
        "owner": "joe",
    }

Status: 200

If a player has drawn the last card in the deck (and will have the last turn)
the data contains an additional ``"lastPlayer"`` property with the pid of this
player.

If the game state is ``"ended"`` the data contains an additional ``"winners"``
property with the pids of the winners.

If the game {gid} doesn't exist:

Status: 404

PUT /games/{gid}
----------------

Can be used to change the state of the game to "started". Requires
authentication (must be game owner).

Request
^^^^^^^

Game object with "state" property (other properties are ignored)::

    { "state": "started" }

Response
^^^^^^^^

On success:

Status: 204

On failure:

Object with "messages" property::

    { "messages": ["Game must have at least 3 players"] }

Status: 400

DELETE /games/{gid}
^^^^^^^^^^^^^^^^^^^

Deletes a game. Only for game owner.

Response
^^^^^^^^

Status: 204

GET /games/{gid}/players
------------------------

Response
^^^^^^^^

The list of players for game {gid}::

    {
        "players": [
            {
                "cards": {
                    "blue": 2,
                    "green": 0,
                    "purple": 0,
                    "red": 0,
                    "yellow": 3
                },
                "gid": 1,
                "pid": 1,
                "username": "joe",
            },
            {
                "cards": {
                    "blue": 0,
                    "green": 3,
                    "purple": 0,
                    "red": 1,
                    "yellow": 2
                },
                "gid": 1,
                "pid": 2,
                "username": "alice",
            },
            {
                "cards": {
                    "blue": 0,
                    "green": 3,
                    "purple": 0,
                    "red": 1,
                    "yellow": 2
                },
                "gid": 1,
                "pid": 3,
                "username": "bob",
            }
        ]
    }


POST /games/{gid}/players
-------------------------

Requires authentication.

Response
^^^^^^^^

If successful:

The new player's data::

    {
        "cards": {
            "blue": 0,
            "green": 0,
            "purple": 0,
            "red": 0,
            "yellow": 0
        },
        "gid": 1,
        "pid": 1,
        "username": "joe",
    }

Status: 201
Headers: Location with URI of new player

If unsuccessful:

A list of messages::

    { "messages": ["You are already in this game"] }

Status: 400

GET /games/{gid}/players/{pid}
------------------------------

Requires authentication.

Response
^^^^^^^^

If the player {pid} exists for game {gid}:

Player's data::

    {
        "cards": {
            "blue": 2,
            "green": 0,
            "purple": 0,
            "red": 0,
            "yellow": 3
        },
        "gid": 1,
        "pid": 1,
        "username": "joe",
    }

Status: 200

If the authenticated user is the player's user or the game state is
``"ended"``, the data contains an additional ``"color"`` property.

If the player doesn't exist:

Status: 404


DELETE /games/{gid}/players/{pid}
---------------------------------

Removes player from game. Requires authentication (must be game owner or
player's user).

Response
^^^^^^^^

Status: 204

GET /games/{gid}/players/{pid}/hand
-----------------------------------

Requires authentication (only player's user).

Response
^^^^^^^^

List of cards in the player's hand::

    { "hand": [ "ninja", "green", "red", "green" ] }

GET /games/{gid}/players/{pid}/moves
------------------------------------

TODO

POST /games/{gid}/players/{pid}/moves
-------------------------------------

Request
^^^^^^^

A move object containing three orders::

    {
        "first": {
            "type": "deploy",
            "to": 2,
            "color": "red"
        },
        "second": {
            "type": "transfer",
            "from": 1,
            "to":  2,
            "color": "red"
        },
        "third": {
            "type": "attack",
            "to": 2,
            "color": "red"
        }
    ]

The first order may be of type "deploy" or ninja.
The second order may be of type "transfer" or "add".
The third order must be of type "attack" or be null.

Response
^^^^^^^^

TODO

GET /games/{gid}/events
-----------------------------

Response
^^^^^^^^

An event stream (Content-Type: text/event-stream) for use with a client
supporting `HTML5 Server-Sent Events`_::

    event: players
    data: { "action": "join", "player": 3 }

    event: state
    data: started

    event: current_player
    data: 3

Events can be of type: ``players``, ``state`` or ``current_player``.

For events of type ``players`` the data is a JSON object with an ``"action"``
attribute (one of ``"join" | "leave"``) and a ``"player"`` attribute with the
pid of a player.

For events of type ``state`` the data is a string describing the new state of
the game.

For events of type ``current_player`` the data is a player's pid.

.. _HTML5 Server-Sent Events: http://www.w3.org/TR/eventsource/

GET /users
----------

Response
^^^^^^^^

The list of users::

    {
        "users": [
            { "username": "alice", "score": 5 },
            { "username": "bob", "score": 2 },
            { "username": "joe", "score": 0 },
        ]
    }

POST /users
-----------

Request
^^^^^^^

A user object with username and password::

    { "username": "joe", "password": "VerySecretPassword" }

Response
^^^^^^^^

If successful:

The new user::

    { "username": "joe", "score": 0 }

Status: 201
Headers: Location with URI of new user

If unsuccesful:

List of messages::

    { "messages": ["Username already taken"] }

Status: 400

GET /users/{username}
---------------------

Response
^^^^^^^^

If user {username} exists:

Data of user::

    { "username": "alice", "score": 5 }

Status: 200

If user doesn't exist:

Status: 400

PUT /users/{username}
---------------------

TODO

DELETE /users/{username}
------------------------

TODO?
