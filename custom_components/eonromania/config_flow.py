"""ConfigFlow și OptionsFlow pentru integrarea EON România."""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_UPDATE, URL_LOGIN, HEADERS_POST

_LOGGER = logging.getLogger(__name__)

class EonRomaniaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionarea ConfigFlow pentru integrarea EON România."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Pasul inițial pentru configurare."""
        errors = {}

        if user_input is not None:
            # Extragem datele introduse
            username = user_input["username"]
            password = user_input["password"]
            cod_incasare = user_input["cod_incasare"]
            update_interval = user_input["update_interval"]

            _LOGGER.debug("Date introduse: username=%s, cod_incasare=%s", username, cod_incasare)

            # Testăm autentificarea
            session = async_get_clientsession(self.hass)
            token = await self._test_authentication(session, username, password)

            if token:
                _LOGGER.debug("Autentificare reușită! Token obținut: %s", token)
                # Salvăm datele în core.config_entries
                return self.async_create_entry(
                    title=f"E-ON România ({cod_incasare})",
                    data={
                        "username": username,
                        "password": password,
                        "cod_incasare": cod_incasare,
                        "update_interval": update_interval
                    },
                )
            else:
                errors["base"] = "auth_failed"
                _LOGGER.error("Autentificare eșuată pentru utilizatorul %s", username)

        # Schema formularului de configurare
        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("cod_incasare"): str,
                vol.Optional("update_interval", default=DEFAULT_UPDATE): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def _test_authentication(self, session: HomeAssistant, username: str, password: str):
        """Testează autentificarea utilizând API-ul."""
        payload = {
            "username": username,
            "password": password,
            "rememberMe": False,
        }

        try:
            async with session.post(URL_LOGIN, json=payload, headers=HEADERS_POST) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("accessToken")
                else:
                    _LOGGER.debug(
                        "Eroare autentificare: Status=%s, Răspuns=%s",
                        response.status,
                        await response.text(),
                    )
        except Exception as e:
            _LOGGER.error("Eroare la conectarea cu API-ul: %s", e)

        return None


class EonRomaniaOptionsFlow(config_entries.OptionsFlow):
    """Gestionarea OptionsFlow pentru integrarea EON România."""

    def __init__(self, config_entry):
        """Inițializează OptionsFlow cu intrarea existentă."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Pasul inițial pentru modificarea opțiunilor."""
        if user_input is not None:
            # Salvăm noile date în config_entry
            _LOGGER.debug("Modificare date: %s", user_input)
            self.hass.config_entries.async_update_entry(self.config_entry, options=user_input)
            return self.async_create_entry(title="", data={})

        # Pregătim schema pentru formularul de modificare
        options_schema = vol.Schema(
            {
                vol.Optional("username", default=self.config_entry.data.get("username", "")): str,
                vol.Optional("password", default=self.config_entry.data.get("password", "")): str,
                vol.Optional("cod_incasare", default=self.config_entry.data.get("cod_incasare", "")): str,
                vol.Optional("update_interval", default=self.config_entry.data.get("update_interval", DEFAULT_UPDATE)): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)