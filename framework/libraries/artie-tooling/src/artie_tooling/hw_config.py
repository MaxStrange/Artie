"""
This module contains the HWConfig class and associated classes.
"""
import dataclasses
import json
import yaml


@dataclasses.dataclass
class SBC:
    """
    A single board computer as described by the config mapping in the K8S cluster.
    """
    name: str
    """The name of the SBC, such as 'controller-node'"""

    architecture: str
    """E.g., linux/arm64"""

    buses: list[str]
    """The list of buses this SBC has access to. These are bus IDs, such as can0."""

@dataclasses.dataclass
class MCU:
    """
    A microcontroller unit as described by the config mapping in the K8S cluster.
    """
    name: str
    """The name of the MCU, such as 'sensor-node'"""

    buses: list[str]
    """The list of buses this MCU has access to. These are bus IDs, such as can0."""

@dataclasses.dataclass
class Sensor:
    """
    A sensor as described by the config mapping in the K8S cluster.
    """
    name: str
    """The name of the sensor, such as 'eye-left'"""

    bus: str
    """The bus this sensor is found on. This is a bus ID, such as csi0."""

@dataclasses.dataclass
class Actuator:
    """
    An actuator as described by the config mapping in the K8S cluster.
    """
    name: str
    """The name of the actuator, such as 'eyebrow-left'"""

    bus: str
    """The bus this actuator is found on. This is a bus ID, such as lcd0."""

@dataclasses.dataclass
class HWConfig:
    artie_type_name: str
    """The type of Artie, such as Artie00"""

    sbcs: list[SBC]
    """The list of single board computers this type of Artie has."""

    mcus: list[MCU]
    """The list of microcontroller units this type of Artie has."""

    sensors: list[Sensor]
    """The list of sensors this type of Artie has."""

    actuators: list[Actuator]
    """The list of actuators this type of Artie has."""

    @staticmethod
    def from_json(fpath: str|bytes) -> "HWConfig":
        """
        Parse a `HWConfig` instance from a JSON file found at `fpath`
        or from a file-like object.
        """
        if hasattr(fpath, 'read'):
            raw = json.load(fpath)
        else:
            with open(fpath, 'r') as f:
                raw = json.load(f)

        api_version = raw.get('api-version', 'v1')
        if api_version == 'v1':
            return HWConfig._from_config_v1(raw)
        else:
            raise NotImplementedError(f"api-version found in HW configuration is not one we know how to handle. Version found: {api_version}")

    @staticmethod
    def from_config(fpath: str|bytes) -> "HWConfig":
        """
        Parse a `HWConfig` instance from a YAML file found at `fpath`
        or from a file-like object.
        """
        if hasattr(fpath, 'read'):
            raw = yaml.safe_load(fpath)
        else:
            with open(fpath, 'r') as f:
                raw = yaml.safe_load(f)

        api_version = raw.get('api-version', 'v1')
        if api_version == 'v1':
            return HWConfig._from_config_v1(raw)
        else:
            raise NotImplementedError(f"api-version found in HW configuration is not one we know how to handle. Version found: {api_version}")

    @staticmethod
    def _from_config_v1(raw):
        if "artie-type-name" not in raw:
            raise KeyError(f"Cannot find 'artie-type-name' in Artie type file")

        if "single-board-computers" not in raw:
            raise KeyError(f"Cannot find 'single-board-computers' in Artie type file")

        if "microcontrollers" not in raw:
            raise KeyError(f"Cannot find 'microcontrollers' in Artie type file")

        if "actuators" not in raw:
            raise KeyError(f"Cannot find 'actuators' in Artie type file")

        return HWConfig(
            artie_type_name=raw["artie-type-name"],
            sbcs=[SBC(**sbc) for sbc in raw["single-board-computers"]],
            mcus=[MCU(**mcu) for mcu in raw["microcontrollers"]],
            sensors=[Sensor(**sensor) for sensor in raw["sensors"]],
            actuators=[Actuator(**actuator) for actuator in raw["actuators"]],
        )

    def to_json_str(self, api_version="v1") -> str:
        """Return a string representing a `HWConfig` in JSON."""
        return json.dumps(dataclasses.asdict(self), indent=2)

    def to_yaml_str(self, api_version="v1") -> str:
        """Return a string representing a `HWConfig` in YAML."""
        return yaml.dump(dataclasses.asdict(self))
