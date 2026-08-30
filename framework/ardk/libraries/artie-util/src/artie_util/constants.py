import enum

class ArtieEnvVariables(enum.StrEnum):
    """
    Various env-mapped configuration keys.

    These come from either the environment variables set in Kubernetes
    (by means of the Helm Chart - see framework/ardk/deploy/artie-base/values.yaml),
    or from the Docker run command line (for testing).

    If you update these, make sure to also update the Helm Chart values
    in framework/ardk/deploy/artie-base/values.yaml under baseEnvironment.
    """
    ARTIE_ID = "ARTIE_ID"
    ARTIE_RUN_MODE = "ARTIE_RUN_MODE"
    ARTIE_GIT_TAG = "ARTIE_GIT_TAG"
    LOG_COLLECTOR_HOSTNAME = "LOG_COLLECTOR_HOSTNAME"
    LOG_COLLECTOR_PORT = "LOG_COLLECTOR_PORT"
    LOG_LEVEL = "ARTIE_LOG_LEVEL"
    METRICS_SERVER_PORT = "METRICS_SERVER_PORT"
    ARTIE_PUBSUB_BROKER_HOSTNAME = "ARTIE_PUBSUB_BROKER_HOSTNAME"
    ARTIE_PUBSUB_BROKER_PORT = "ARTIE_PUBSUB_BROKER_PORT"
    ARTIE_PUBSUB_USE_SSL = "ARTIE_PUBSUB_USE_SSL"
    ARTIE_SERVICE_BROKER_HOSTNAME = "ARTIE_SERVICE_BROKER_HOSTNAME"
    ARTIE_SERVICE_BROKER_PORT = "ARTIE_SERVICE_BROKER_PORT"

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

class StatusLEDStates(enum.StrEnum):
    """
    The different status LED states.
    """
    ON = "on"
    OFF = "off"
    HEARTBEAT = "heartbeat"
    UNKNOWN = "unknown"
