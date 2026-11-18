from copy import deepcopy

import pandas as pd


class Experiment:
    """Store experimental data, parameters, metadata and processing results."""

    def __init__(
        self,
        name,
        data=None,
        *,
        parameters=None,
        metadata=None,
    ):
        self.name = self._validate_name(name)
        self._data = None
        self._parameters = deepcopy(parameters) if parameters is not None else {}
        self._metadata = deepcopy(metadata) if metadata is not None else {}
        self._results = {}

        if not isinstance(self._parameters, dict):
            raise TypeError("parameters must be a dictionary")
        if not isinstance(self._metadata, dict):
            raise TypeError("metadata must be a dictionary")

        if data is not None:
            self.set_data(data)

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Experiment name must be a non-empty string")
        return name.strip()

    @staticmethod
    def _validate_dataframe(data):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

    def set_data(self, data):
        self._validate_dataframe(data)
        self._data = data.copy(deep=True)
        return self

    def get_data(self, *, copy=True):
        if self._data is None:
            raise ValueError("Experiment has no data")
        return self._data.copy(deep=True) if copy else self._data

    @property
    def data(self):
        return self.get_data()

    @property
    def parameters(self):
        return deepcopy(self._parameters)

    @property
    def metadata(self):
        return deepcopy(self._metadata)

    @property
    def results(self):
        return deepcopy(self._results)

    def set_parameter(self, name, value):
        name = self._validate_name(name)
        self._parameters[name] = deepcopy(value)
        return self

    def get_parameter(self, name, default=None):
        return deepcopy(self._parameters.get(name, default))

    def update_parameters(self, parameters):
        if not isinstance(parameters, dict):
            raise TypeError("parameters must be a dictionary")

        for name, value in parameters.items():
            self.set_parameter(name, value)
        return self

    def set_metadata(self, name, value):
        name = self._validate_name(name)
        self._metadata[name] = deepcopy(value)
        return self

    def get_metadata(self, name, default=None):
        return deepcopy(self._metadata.get(name, default))

    def update_metadata(self, metadata):
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary")

        for name, value in metadata.items():
            self.set_metadata(name, value)
        return self

    def add_result(self, name, result, *, replace=False):
        name = self._validate_name(name)

        if name in self._results and not replace:
            raise ValueError(f"Result already exists: {name}")

        self._results[name] = deepcopy(result)
        return self

    def get_result(self, name, default=None):
        return deepcopy(self._results.get(name, default))

    def remove_result(self, name):
        if name not in self._results:
            raise KeyError(f"Unknown result: {name}")
        return self._results.pop(name)

    def list_results(self):
        return list(self._results.keys())

    def __repr__(self):
        rows = 0 if self._data is None else len(self._data)
        return (
            f"Experiment(name={self.name!r}, "
            f"rows={rows}, results={len(self._results)})"
        )
