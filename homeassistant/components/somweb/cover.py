import logging
import voluptuous as vol
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.components.cover import (
    DEVICE_CLASS_GARAGE,
    PLATFORM_SCHEMA,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    CoverEntity,
)
from somweb import SomwebClient as Client, DoorStatusType, Door

_LOGGER = logging.getLogger(__name__)
_TOKEN = None

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the SOMweb platform."""
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    somweb_udi = config[CONF_ID]

    client = Client(somweb_udi, username, password)
    if not await client.is_alive():
        _LOGGER.error(
            "SOMweb with provided UDI '%s' not found on this network", somweb_udi
        )
        return False

    auth_result = await client.authenticate()
    if not auth_result.success:
        _LOGGER.error("Failed to authenticate (udi=%s)", somweb_udi)
        return False

    global _TOKEN  # pylint: disable=global-statement.
    _TOKEN = auth_result.token

    entities = [
        SomWebDoor(client, door)
        for door in client.get_doors_from_page_content(auth_result.page_content)
    ]

    doorCount = len(entities)
    _LOGGER.info("Found %d door%s.", doorCount, "s" if doorCount > 1 else "")
    async_add_entities(entities)
    return True


class SomWebDoor(CoverEntity):
    """Representation of a SOMweb Garage Door."""

    def __init__(self, client: Client, door: Door):
        self._client: Client = client
        self._id: int = door.id
        self._name: str = door.name
        self._state: DoorStatusType = None
        self._is_opening: bool = False
        self._is_closing: bool = False
        self._unique_id: str = f"{client.udi}_{door.id}"
        self._available: bool = True
        self._id_in_log = f"'{self._name} ({client.udi}_{door.id})'"

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
        """Current position where 0 means closed and 100 is fully open. None if Unknown."""
        return (
            0
            if self._state == DoorStatusType.Closed
            else 100
            if self._state == DoorStatusType.Open
            else None
        )

    @property
    def is_closed(self):
        """Return the state of the cover."""
        return (
            None
            if self._state == None or self._state == DoorStatusType.Unknown
            else self._state == DoorStatusType.Closed
        )

    @property
    def is_opening(self):
        """Return the state of the cover."""
        return self._is_opening

    @property
    def is_closing(self):
        """Return the state of the cover."""
        return self._is_closing

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_GARAGE

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Open cover %s", self._id_in_log)

        try:
            self._is_opening = True
            self.async_write_ha_state()
            if not await self._client.open_door(_TOKEN, self._id):
                _LOGGER.error("Unable to open cover %s", self._id_in_log)
            else:
                await self._client.wait_for_door_state(self._id, DoorStatusType.Open)
        except:
            _LOGGER.exception("Exception when opening cover %s", self._id_in_log)
        finally:
            self._is_opening = False
            await self._force_update()

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        _LOGGER.debug("Close cover %s", self._id_in_log)

        try:
            self._is_closing = True
            self.async_write_ha_state()
            if not await self._client.close_door(_TOKEN, self._id):
                _LOGGER.error("Unable to close cover %s", self._id_in_log)
            else:
                await self._client.wait_for_door_state(self._id, DoorStatusType.Closed)
        except:
            _LOGGER.exception("Exception when closing cover %s", self._id_in_log)
        finally:
            self._is_closing = False
            await self._force_update()

    async def _force_update(self):
        """Force update of data."""
        _LOGGER.debug("Force update state of cover %s", self._id_in_log)
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    async def __async_refresh_state(self) -> bool:
        """Refresh SOMweb cover state."""
        try:
            self._state = await self._client.get_door_status(self._id)
            _LOGGER.debug(
                "Current state of cover %s is '%s'", self._id_in_log, self._state.name
            )

            return self._state != DoorStatusType.Unknown
        except:
            self._state = DoorStatusType.Unknown
            _LOGGER.exception(
                "Exception when getting state of cover %s", self._id_in_log
            )
            return False

    async def __async_re_connect(self) -> bool:
        """Re-connect SOMweb."""
        try:
            if not self._client.is_alive():
                _LOGGER.debug("Somweb with id %s is not alive", self._client.udi)
                return False

            _LOGGER.debug(
                "Attempting to re-authenticate somweb for cover %s", self._id_in_log
            )
            authResult = await self._client.authenticate()
            if authResult.success and len(authResult.token) > 0:
                _LOGGER.info(
                    "Successfully re-authenticated somweb for cover %s",
                    self._id_in_log,
                )
                global _TOKEN  # pylint: disable=global-statement.
                _TOKEN = authResult.token
                return True
            else:
                _LOGGER.warn(
                    "Failed re-authenticating somweb for cover %s", self._id_in_log
                )
        except:
            _LOGGER.exception(
                "Exception when re-authenticating somweb for cover %s",
                self._id_in_log,
            )

        return False

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs):
        """Get the latest status from SOMweb."""
        if not (
            await self.__async_refresh_state()
            or (await self.__async_re_connect() and await self.__async_refresh_state())
        ):
            _LOGGER.warn("SOMweb seems to be off the grid. Will continue attempts...")

        self._available = self._state != DoorStatusType.Unknown
