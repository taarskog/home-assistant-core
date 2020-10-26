"""SOMweb garage door integration."""

# import logging

# from somweb import SomwebClient as Client

# import voluptuous as vol
# from voluptuous.schema_builder import Self

# from homeassistant.helpers import discovery
# import homeassistant.helpers.config_validation as cv

# from homeassistant.const import (
#     CONF_ID,
#     CONF_PASSWORD,
#     CONF_USERNAME,
# )

# _LOGGER = logging.getLogger(__name__)

# DOMAIN = "somweb"

# CLIENT = None

# CONFIG_SCHEMA = vol.Schema(
#     {
#         DOMAIN: vol.Schema(
#             {
#                 vol.Required(CONF_ID): cv.string,
#                 vol.Required(CONF_USERNAME): cv.string,
#                 vol.Required(CONF_PASSWORD): cv.string,
#             }
#         )
#     },
#     extra=vol.ALLOW_EXTRA,
# )


# def setup(hass, config):
#     """Set up the SOMweb component."""
#     global CLIENT  # pylint: disable=global-statement.

#     username = config[DOMAIN][CONF_USERNAME]
#     password = config[DOMAIN][CONF_PASSWORD]
#     somWebUDI = config[DOMAIN][CONF_ID]

#     CLIENT = Client(somWebUDI, username, password)

#     # Verify that passed in configuration works.
#     if not CLIENT.authenticate():
#         _LOGGER.warn("Failed to authenticate")
#         return False

#     discovery.load_platform(hass, "cover", DOMAIN, {}, config)
#     return True
