import enum

class ArtieEnvVariables(enum.StrEnum):
    """
    Various env-mapped configuration keys.
    """
    ARTIE_ID = "ARTIE_ID"
    ARTIE_RUN_MODE = "ARTIE_RUN_MODE"
    ARTIE_GIT_TAG = "ARTIE_GIT_TAG"
    LOG_COLLECTOR_HOSTNAME = "LOG_COLLECTOR_HOSTNAME"
    LOG_COLLECTOR_PORT = "LOG_COLLECTOR_PORT"
    METRICS_SERVER_PORT = "METRICS_SERVER_PORT"

class ArtieRunModes(enum.StrEnum):
    """
    The different types of run modes, which are the possible values for the ARTIE_RUN_MODE env key.
    """
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    SANITY_TESTING = "sanity"
    UNIT_TESTING = "unit"
    INTEGRATION_TESTING = "integration"

class SubmoduleStatuses(enum.StrEnum):
    """
    The different values that a submodule status check can take on.
    """
    WORKING = "working"
    DEGRADED = "degraded"
    NOT_WORKING = "not working"
    UNKNOWN = "unknown"
