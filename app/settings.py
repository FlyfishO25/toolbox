import config
import ui


FEATURES_CONFIG_KEY = "enabled_features"


def _load_feature_states():
    states = config.get(FEATURES_CONFIG_KEY, {})
    return dict(states) if isinstance(states, dict) else {}


def is_enabled(feature_key):
    state = _load_feature_states().get(feature_key)
    return True if state is None else bool(state)


def _build_items(features):
    return [
        {
            "label": feature["label"],
            "type": ui.ITEM_TOGGLE,
            "state": is_enabled(feature["key"]),
        }
        for feature in features
    ]


def _save_states(features, states):
    current = _load_feature_states()
    for feature, state in zip(features, states):
        current[feature["key"]] = bool(state)
    config.set(FEATURES_CONFIG_KEY, current)


def main(features):
    if not features:
        ui.alert("No configurable features were found.", title="Settings")
        return

    result = ui.select(
        _build_items(features),
        title="Settings",
        search=False,
        action_label="confirm",
    )
    if result is None:
        return

    _save_states(features, result["states"])
    ui.alert(
        "Feature visibility updated.\n\nReturn home to see the updated menu.",
        title="Settings",
    )
