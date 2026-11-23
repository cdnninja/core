"""Tests for Plex media_players."""

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from plexapi.exceptions import NotFound
import pytest
from pytest_homeassistant.common import MockConfigEntry
import requests_mock

from homeassistant.components.plex.server import PlexServer
from homeassistant.const import STATE_PLAYING
from homeassistant.core import HomeAssistant

from .conftest import plex_server_url
from .helpers import trigger_plex_update

MEDIA_PLAYER = "media_player.plex_plex_for_android_tv_shield_android_tv"


async def test_plex_tv_clients(
    hass: HomeAssistant,
    entry,
    setup_plex_server,
    requests_mock: requests_mock.Mocker,
    player_plexhtpc_resources,
) -> None:
    """Test getting Plex clients from plex.tv."""
    requests_mock.get("/resources", text=player_plexhtpc_resources)

    with patch("plexapi.myplex.MyPlexResource.connect", side_effect=NotFound):
        await setup_plex_server()
        await hass.async_block_till_done()

    media_players_before = len(hass.states.async_entity_ids("media_player"))
    await hass.config_entries.async_unload(entry.entry_id)

    # Ensure one more client is discovered
    await setup_plex_server()
    media_players_after = len(hass.states.async_entity_ids("media_player"))
    assert media_players_after == media_players_before + 1

    await hass.config_entries.async_remove(entry.entry_id)

    # Ensure only plex.tv resource client is found
    with patch("plexapi.server.PlexServer.sessions", return_value=[]):
        await setup_plex_server(disable_clients=True)

    assert len(hass.states.async_entity_ids("media_player")) == 1


@pytest.mark.usefixtures("mock_plex_server")
async def test_media_player_markers(
    hass: HomeAssistant, requests_mock: requests_mock.Mocker
) -> None:
    """Test intro and credits markers of the active session are exposed."""
    state = hass.states.get(MEDIA_PLAYER)
    assert state.attributes["media_intro_start"] == 0
    assert state.attributes["media_intro_end"] == 85
    assert state.attributes["media_credits_start"] == 8700

    assert any(
        request.path == "/library/metadata/1"
        and request.qs.get("includemarkers") == ["1"]
        for request in requests_mock.request_history
    )


async def test_media_player_markers_not_found(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    setup_plex_server: Callable[..., Awaitable[PlexServer]],
    requests_mock: requests_mock.Mocker,
) -> None:
    """Test a session is still tracked when its markers cannot be fetched."""
    requests_mock.get(
        f"{plex_server_url(entry)}/library/metadata/1", status_code=HTTPStatus.NOT_FOUND
    )
    await setup_plex_server()

    state = hass.states.get(MEDIA_PLAYER)
    assert state.state == STATE_PLAYING
    assert "media_intro_start" not in state.attributes
    assert "media_intro_end" not in state.attributes
    assert "media_credits_start" not in state.attributes


@pytest.mark.usefixtures("mock_plex_server")
async def test_media_player_markers_media_changed(
    hass: HomeAssistant, mock_websocket: MagicMock
) -> None:
    """Test markers are replaced when the session plays new media."""
    assert "media_credits_start" in hass.states.get(MEDIA_PLAYER).attributes

    trigger_plex_update(
        mock_websocket,
        payload={
            "PlaySessionStateNotification": [
                {
                    "sessionKey": "1",
                    "ratingKey": "100",
                    "viewOffset": 5050,
                    "state": "playing",
                }
            ]
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(MEDIA_PLAYER)
    assert state.attributes["media_content_id"] == 100
    assert "media_intro_start" not in state.attributes
    assert "media_intro_end" not in state.attributes
    assert "media_credits_start" not in state.attributes
