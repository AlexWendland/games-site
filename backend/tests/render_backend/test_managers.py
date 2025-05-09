from typing import Self, override
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from games_backend import models
from games_backend.managers import BookManager, SessionManager

# -------------------------------------
# SessionManager tests
# -------------------------------------


class DummyWebSocket:
    def __init__(self, client_id: str):
        self.client = client_id  # Simulate .client attribute for logging
        self.client_id = client_id

    @override
    def __hash__(self):
        return hash(self.client_id)

    @override
    def __eq__(self, other: Self):
        return isinstance(other, DummyWebSocket) and self.client_id == other.client_id


@pytest.fixture
def session() -> SessionManager:
    return SessionManager(max_players=3)


def test_add_and_get_client_position(session: SessionManager):
    client = Mock()
    session.add_client(client, "Alice")
    assert session.get_client_position(client) is None


def test_move_client_position(session: SessionManager):
    client = Mock()
    session.add_client(client, "Bob")
    session._move_client_position(client, 1)
    assert session.get_client_position(client) == 1
    assert session._get_positions()[1] == "Bob"
    session._move_client_position(client, 2)
    assert session.get_client_position(client) == 2
    assert session._get_positions()[1] is None
    assert session._get_positions()[2] == "Bob"


def test_position_conflict(session: SessionManager):
    c1, c2 = Mock(), Mock()
    session.add_client(c1, "One")
    session.add_client(c2, "Two")
    session._move_client_position(c1, 0)
    with pytest.raises(ValueError):
        session._move_client_position(c2, 0)


def test_remove_client(session: SessionManager):
    client = Mock()
    session.add_client(client, "Alice")
    session._move_client_position(client, 1)
    session.remove_client(client)
    assert client not in session._player_names
    assert client not in session._player_to_position
    assert session._get_positions()[1] is None


def test_get_positions(session: SessionManager):
    c1, c2 = Mock(), Mock()
    session.add_client(c1, "Alpha")
    session.add_client(c2, "Beta")
    session._move_client_position(c1, 0)
    session._move_client_position(c2, 1)
    positions = session._get_positions()
    assert positions[0] == "Alpha"
    assert positions[1] == "Beta"


def test_invalid_client_operations(session: SessionManager):
    fake = Mock()
    with pytest.raises(ValueError):
        session.get_client_position(fake)
    with pytest.raises(ValueError):
        session._move_client_position(fake, 0)
    with pytest.raises(ValueError):
        session.remove_client(fake)
    with pytest.raises(ValueError):
        session._set_client_name(fake, "Other name")


def test_get_positions(session: SessionManager):
    c1, c2 = Mock(), Mock()
    session.add_client(c1, "Alpha")
    session.add_client(c2, "Beta")
    session._move_client_position(c1, 0)
    session._move_client_position(c2, 1)
    session._set_client_name(c1, "Charlie")
    positions = session._get_positions()
    assert positions[0] == "Charlie"
    assert positions[1] == "Beta"


def test_set_player_name(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)

    response = session.handle_function_call(client, "set_player_name", {"player_name": "Alice"})
    assert response is None
    assert session._player_names[client] == "Alice"


def test_set_player_name_invalid(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)

    response = session.handle_function_call(client, "set_player_name", {"player_name": 123})
    assert isinstance(response, models.ErrorResponse)
    assert "Parameter validation failed" in response.parameters.error_message


def test_set_player_position(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)

    response = session.handle_function_call(client, "set_player_position", {"new_position": 1})
    assert response is None
    assert session.get_client_position(client) == 1
    assert session._position_to_player[1] == client


def test_set_player_position_already_taken(session: SessionManager):
    client1 = DummyWebSocket("c1")
    client2 = DummyWebSocket("c2")
    session.add_client(client1)
    session.add_client(client2)

    session.handle_function_call(client1, "set_player_position", {"new_position": 1})
    response = session.handle_function_call(client2, "set_player_position", {"new_position": 1})

    assert isinstance(response, models.ErrorResponse)
    assert "already taken" in response.parameters.error_message


def test_set_player_position_invalid(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)

    response = session.handle_function_call(
        client, "set_player_position", {"new_position": "one"}
    )
    assert isinstance(response, models.ErrorResponse)
    assert "Parameter validation failed" in response.parameters.error_message


def test_leave_player_position(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)
    session.handle_function_call(client, "set_player_position", {"new_position": 0})

    response = session.handle_function_call(client, "leave_player_position", {})
    assert response is None
    assert session.get_client_position(client) is None
    assert session._position_to_player[0] is None


def test_unknown_function_name(session: SessionManager):
    client = DummyWebSocket("c1")
    session.add_client(client)

    response = session.handle_function_call(client, "do_nothing", {})
    assert isinstance(response, models.ErrorResponse)
    assert "not supported" in response.parameters.error_message


# -------------------------------------
# BookManager tests
# -------------------------------------


@pytest.fixture
def book_manager():
    return BookManager()


@pytest.fixture
def mock_game_manager() -> MagicMock:
    game_manager = MagicMock()
    game_manager.close_game = AsyncMock()
    return game_manager


def test_add_and_get_game(book_manager: BookManager, mock_game_manager: MagicMock):
    game_id = "game1"
    book_manager.add_game(game_id, mock_game_manager)
    retrieved = book_manager.get_game(game_id)
    assert retrieved == mock_game_manager


def test_add_duplicate_game_raises(book_manager: BookManager, mock_game_manager: MagicMock):
    game_id = "game1"
    book_manager.add_game(game_id, mock_game_manager)
    with pytest.raises(KeyError, match="already exists"):
        book_manager.add_game(game_id, mock_game_manager)


def test_get_nonexistent_game_raises(book_manager: BookManager):
    with pytest.raises(KeyError, match="does not exist"):
        book_manager.get_game("no_such_game")


@pytest.mark.asyncio
async def test_remove_game(book_manager: BookManager, mock_game_manager: MagicMock):
    game_id = "game1"
    book_manager.add_game(game_id, mock_game_manager)
    await book_manager.remove_game(game_id)
    mock_game_manager.close_game.assert_awaited_once()
    assert game_id not in book_manager.get_all_game_ids()


def test_get_all_game_ids(book_manager: BookManager, mock_game_manager: MagicMock):
    ids = {"a", "b", "c"}
    for game_id in ids:
        book_manager.add_game(game_id, mock_game_manager)
    assert book_manager.get_all_game_ids() == ids


# -------------------------------------
# GameManager tests
# -------------------------------------
