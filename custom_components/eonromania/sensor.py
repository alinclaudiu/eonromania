"""Platforma Sensor pentru EON România."""
import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Configurarea senzorilor pentru fiecare intrare definită în config_entries
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configurează senzorii pentru o intrare."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id]
    
    # Creăm senzori pentru fiecare dispozitiv în funcție de datele disponibile
    sensors = [
        DateContractSensor(coordinators["dateuser"], config_entry),
    ]

    # Adăugăm senzori pentru fiecare dispozitiv din `indexDetails`
    citireindex_data = coordinators["citireindex"].data
    if citireindex_data:
        devices = citireindex_data.get("indexDetails", {}).get("devices", [])
        _LOGGER.debug("Dispozitive detectate în citireindex_data: %s", devices)  # Log pentru dispozitive
        seen_devices = set()  # Set pentru a preveni duplicările
        for device in devices:
            device_number = device.get("deviceNumber", "unknown_device")
            if device_number not in seen_devices:
                sensors.append(CitireIndexSensor(coordinators["citireindex"], config_entry, device_number))
                seen_devices.add(device_number)  # Adăugăm device_number în set
            else:
                _LOGGER.warning("Dispozitiv duplicat ignorat: %s", device_number)
    
    # Gestionăm senzorii de arhivă
    arhiva_data = coordinators["arhiva"].data
    if arhiva_data:
        for year_data in arhiva_data.get("history", []):
            year = year_data.get("year")
            if year:
                sensors.append(ArhivaSensor(coordinators["arhiva"], config_entry, year))

    async_add_entities(sensors)

# Senzor pentru afișarea datelor contractului utilizatorului
class DateContractSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea datelor contractului."""

    def __init__(self, coordinator, config_entry):
        """Inițializează senzorul DateContractSensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Date contract"
        self._attr_unique_id = f"{DOMAIN}_date_contract_{self.config_entry.entry_id}"
        self._attr_entity_id = f"sensor.date_contract_{config_entry.data['cod_incasare']}"  # corect


        # Debug pentru inițializare
        _LOGGER.debug(
            "Inițializare DateContractSensor: name=%s, unique_id=%s",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def state(self):
        """Returnează starea senzorului."""
        if not self.coordinator.data:
            _LOGGER.debug("Senzor DateContractSensor - Nu există date în coordinator.data.")
            return None

        state_value = self.coordinator.data.get("accountContract")
        _LOGGER.debug("Senzor DateContractSensor - Starea datelor pe senzor: %s", state_value)
        return state_value

    @property
    def extra_state_attributes(self):
        """Returnează atributele adiționale ale senzorului."""
        if not self.coordinator.data:
            _LOGGER.debug("Senzor DateContractSensor - Nu există date în coordinator.data.")
            return {}

        reading_period = self.coordinator.data.get("readingPeriod", {})
        raw_data = self.coordinator.data

        attributes = {
            "Cod încasare": raw_data.get("accountContract"),
            "Cod loc de consum (NLC)": raw_data.get("consumptionPointCode"),
            "CLC - Cod punct de măsură": raw_data.get("pod"),
            "Operator de Distribuție (OD)": raw_data.get("distributorName"),
            "Preț final (fără TVA)": f"{raw_data.get('supplierAndDistributionPrice', {}).get('contractualPrice')} lei",
            "Preț final (cu TVA)": f"{raw_data.get('supplierAndDistributionPrice', {}).get('contractualPriceWithVat')} lei",
            "Preț furnizare": f"{raw_data.get('supplierAndDistributionPrice', {}).get('priceComponents', {}).get('supplierPrice')} lei/kWh",
            "Tarif reglementat distribuție": f"{raw_data.get('supplierAndDistributionPrice', {}).get('priceComponents', {}).get('distributionPrice')} lei/kWh",
            "Tarif reglementat transport": f"{raw_data.get('supplierAndDistributionPrice', {}).get('priceComponents', {}).get('transportPrice')} lei/kWh",
            "PCS": str(raw_data.get("supplierAndDistributionPrice", {}).get("pcs")),
            "Adresă consum": f"{raw_data.get('consumptionPointAddress', {}).get('street', {}).get('streetType', {}).get('label')} {raw_data.get('consumptionPointAddress', {}).get('street', {}).get('streetName')} {raw_data.get('consumptionPointAddress', {}).get('streetNumber')} ap. {raw_data.get('consumptionPointAddress', {}).get('apartment')}, {raw_data.get('consumptionPointAddress', {}).get('locality', {}).get('localityName')}",
        }
        _LOGGER.debug("Senzor DateContractSensor - Atribute: %s", attributes)
        return attributes

    @property
    def unique_id(self):
        """Returnează identificatorul unic al senzorului."""
        return f"{DOMAIN}_eonromania_contract_{self.config_entry.data['cod_incasare']}"

    @property
    def entity_id(self):
        """Returnează identificatorul explicit al entității."""
        return self._attr_entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează identificatorul explicit al entității."""
        self._attr_entity_id = value

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:file-document-edit-outline"

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "eonromania")},
            "name": "Interfață UI pentru E-ON România",
            "manufacturer": "E-ON România",
            "model": "E-ON România X3",
            "entry_type": DeviceEntryType.SERVICE,
        }

# Senzor pentru afișarea datelor despre indexul curent
class CitireIndexSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea datelor despre indexul curent."""

    def __init__(self, coordinator, config_entry, device_number):
        """Inițializează senzorul CitireIndexSensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.device_number = device_number  # Atribuim device_number

        # Creăm un unique_id unic pentru fiecare dispozitiv
        self._attr_name = "Index curent"
        self._attr_unique_id = f"{DOMAIN}_index_curent_{self.config_entry.entry_id}_{device_number}"
        self._attr_entity_id = f"sensor.index_curent_{self.config_entry.data['cod_incasare']}" # corect


        # Debug pentru inițializare
        _LOGGER.debug(
            "Inițializare CitireIndexSensor: name=%s, unique_id=%s, device_number=%s",
            self._attr_name,
            self._attr_unique_id,
            self.device_number,
        )

    @property
    def state(self):
        """Returnează starea senzorului."""
        if not self.coordinator.data:
            _LOGGER.debug("Senzor CitireIndexSensor - Nu există date în coordinator.data.")
            return None

        # Debug pentru date brute
        _LOGGER.debug("Senzor CitireIndexSensor - Date brute din coordinator.data: %s", self.coordinator.data)

        # Verificăm dacă există secțiunea indexDetails
        index_details = self.coordinator.data.get("indexDetails")
        if not index_details:
            _LOGGER.debug("Senzor CitireIndexSensor - Secțiunea indexDetails lipsește.")
            return None

        # Accesăm dispozitivele
        devices = index_details.get("devices", [])
        if not devices:
            _LOGGER.debug("Senzor CitireIndexSensor - Nu există dispozitive în indexDetails.")
            return None

        # Obținem valoarea curentă a indexului și o convertim în număr întreg
        current_index = devices[0].get("indexes", [{}])[0].get("currentValue")
        current_index = int(current_index) if current_index is not None else None
        _LOGGER.debug("Senzor CitireIndexSensor - Valoarea curentă a indexului: %s", current_index)
        return current_index

    @property
    def extra_state_attributes(self):
        """Returnează atributele adiționale ale senzorului."""
        if not self.coordinator.data:
            _LOGGER.debug("Senzor CitireIndexSensor - Nu există date în coordinator.data.")
            return {}

        # Verificăm dacă există secțiunea indexDetails
        index_details = self.coordinator.data.get("indexDetails")
        if not index_details:
            _LOGGER.debug("Senzor CitireIndexSensor - Secțiunea indexDetails lipsește.")
            return {}

        devices = index_details.get("devices", [])
        if not devices:
            _LOGGER.debug("Senzor CitireIndexSensor - Nu există dispozitive.")
            return {}

        first_device = devices[0]
        first_index = first_device.get("indexes", [{}])[0]
        reading_period = self.coordinator.data.get("readingPeriod", {})

        attributes = {
            "Numărul dispozitivului": first_device.get("deviceNumber"),
            "Data de început a citirii": reading_period.get("startDate"),
            "Data de final a citirii": reading_period.get("endDate"),
            "Citirea contorului permisă": "Da" if reading_period.get("allowedReading") else "Nu",
            "Permite modificarea citirii": "Da" if reading_period.get("allowChange") else "Nu",
            "Dispozitiv inteligent": "Da" if reading_period.get("smartDevice") else "Nu",
            "Tipul citirii curente": "Autocitire" if reading_period.get("currentReadingType") == "02" else "Citire distribuitor" if reading_period.get("currentReadingType") == "01" else "Necunoscut",
            "Citire anterioară": first_index.get("minValue"),
            "Ultima citire validată": first_index.get("oldValue"),
            "Index propus pentru facturare": first_index.get("currentValue"),
            "Trimis la": first_index.get("sentAt"),
            "Poate fi modificat până la": first_index.get("canBeChangedTill"),
        }

        _LOGGER.debug("Senzor CitireIndexSensor - Atribute: %s", attributes)
        return attributes

    @property
    def unique_id(self):
        """Returnează identificatorul unic al senzorului."""
        return f"{DOMAIN}_citire_index{self.config_entry.entry_id}_{self.device_number}"

    @property
    def entity_id(self):
        """Returnează identificatorul explicit al entității."""
        return self._attr_entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează identificatorul explicit al entității."""
        self._attr_entity_id = value

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:gauge"

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "eonromania")},
            "name": "Interfață UI pentru E-ON România",
            "manufacturer": "E-ON România",
            "model": "E-ON România X3",
            "entry_type": DeviceEntryType.SERVICE,
        }

# Senzor pentru afișarea datelor istorice ale consumului
class ArhivaSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea datelor istorice ale consumului."""

    def __init__(self, coordinator, config_entry, year):
        """Inițializează senzorul ArhivaSensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.year = year
        self._attr_name = f"Arhivă - {year}"
        self._attr_unique_id = f"{DOMAIN}_arhiva_{self.config_entry.entry_id}_{self.year}"
        self._attr_entity_id = f"sensor.arhiva_{self.config_entry.data['cod_incasare']}_{self.year}" # corect


        _LOGGER.debug(
            "Inițializare ArhivaSensor: name=%s, unique_id=%s, year=%s",
            self._attr_name,
            self._attr_unique_id,
            self.year,
        )

    @property
    def state(self):
        """Returnează starea senzorului."""
        # Exemplu: Returnăm numărul total al lunilor disponibile pentru anul respectiv
        year_data = next((y for y in self.coordinator.data.get("history", []) if y["year"] == self.year), None)
        if not year_data:
            return None
        return len(year_data.get("meters", [])[0].get("indexes", [])[0].get("readings", []))

    @property
    def extra_state_attributes(self):
        """Returnează atributele adiționale ale senzorului."""
        year_data = next((y for y in self.coordinator.data.get("history", []) if y["year"] == self.year), None)
        if not year_data:
            return {}

        attributes = {
            "An": self.year,
            "Indexuri": year_data,
            "raw_json": year_data,  # Include date brute pentru diagnosticare
        }
        _LOGGER.debug("Senzor ArhivaSensor - Atribute: %s", attributes)
        return attributes

    @property
    def unique_id(self):
        """Returnează identificatorul unic al senzorului."""
        #return f"{DOMAIN}_arhiva_{config_entry.entry_id}_{year}"
        return f"{DOMAIN}_arhiva_{self.config_entry.entry_id}_{self.year}"
        #self._attr_unique_id = f"{DOMAIN}_arhiva_{config_entry.entry_id}_{year}"
        #return f"{DOMAIN}_arhiva_{self.config_entry.data['cod_incasare']}"

    @property
    def entity_id(self):
        """Returnează identificatorul explicit al entității."""
        return self._attr_entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează identificatorul explicit al entității."""
        self._attr_entity_id = value

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:clipboard-text-clock"

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "eonromania")},
            "name": "Interfață UI pentru E-ON România",
            "manufacturer": "E-ON România",
            "model": "E-ON România X3",
            "entry_type": DeviceEntryType.SERVICE,
        }  