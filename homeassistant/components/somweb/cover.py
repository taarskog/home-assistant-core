"""Platform for operating SOMMER garage doors."""

import logging

from somweb import DoorStatusType, SomwebClient as Client
import voluptuous as vol
from voluptuous.schema_builder import Self

from homeassistant.components.cover import (
    DEVICE_CLASS_GARAGE,
    PLATFORM_SCHEMA,
    STATE_CLOSED,
    STATE_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    CoverEntity,
)
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CLIENT = None

STATES_MAP = {
    DoorStatusType.Closed: STATE_CLOSED,
    DoorStatusType.Open: STATE_OPEN,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the SOMweb platform."""
    global CLIENT  # pylint: disable=global-statement.

    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    somWebUDI = config[CONF_ID]

    CLIENT = Client(somWebUDI, username, password)

    # Verify that passed in configuration works.
    if not CLIENT.authenticate():
        _LOGGER.warn("Failed to authenticate")
        return False

    entities = [SomWebDoor(door) for door in CLIENT.getDoors()]
    _LOGGER.warn(f"Found {len(entities)} door(s).")
    add_entities(entities)  # , True)
    return True


class SomWebDoor(CoverEntity):
    """Representation of a SOMweb Garage Door."""

    def __init__(self, door):
        self._id = door.id
        self._name = door.name
        self._state = None
        self._unique_id = f"{CLIENT.udi}_{door.id}"
        self._available = True

    @property
    def unique_id(self):
        """Unique id of the cover."""
        return self._unique_id

    @property
    def name(self):
        """Name of the cover."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def current_cover_position(self):
        """Current position where 0 menas closed and 100 is fully open."""
        return 0 if self._state == STATE_CLOSED else 100

    @property
    def is_closed(self):
        """Return the state of the cover."""
        return self._state == STATE_CLOSED

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_GARAGE

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE

    def update(self):
        self._update(0)

    def open_cover(self, **kwargs):
        """Open cover."""
        CLIENT.openDoor(self._id)

    def close_cover(self, **kwargs):
        """Close cover."""
        CLIENT.closeDoor(self._id)

    def _update(self, retryCount: int):
        try:
            self._state = STATES_MAP[CLIENT.getDoorStatus(self._id)]
            self._available = True
        except:
            self._available = False
            if retryCount > 0:
                _LOGGER.error(
                    "Unable to update status for door %s [retried %d time(s)]",
                    self._unique_id,
                    retryCount,
                )
                return

            _LOGGER.warn(
                "Exception getting status for door %s - trying to reConnect [retried %d time(s)]",
                self._unique_id,
                retryCount,
            )

            if not self._reConnect():
                return

            self._update(retryCount + 1)

    def _reConnect(self) -> bool:
        if not CLIENT.isReachable():
            _LOGGER.error("Device not reachable when handling door %s", self._unique_id)
            return False

        if not CLIENT.authenticate():
            _LOGGER.error(
                "Re-authentication failed when handling door %s", self._unique_id
            )
            return False

        return True
