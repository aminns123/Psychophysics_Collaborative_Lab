"""Public discovery helpers, loaded lazily so declarations can be imported alone."""


def get_experiment(experiment_id):
    from ._internal.registry import get_experiment as lookup
    return lookup(experiment_id)


def list_experiments(*, include_historical=False):
    from ._internal.registry import list_experiments as listing
    return listing(include_historical=include_historical)
