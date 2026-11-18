from pathlib import Path

import pandas as pd

from data.csv_loader import load_csv_file


class DataManager:
    """Manage named experimental datasets."""

    def __init__(self):
        self._datasets = {}

    def add_data(self, name, dataframe, *, replace=False):
        name = self._validate_name(name)

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")

        if name in self._datasets and not replace:
            raise ValueError(f"Dataset already exists: {name}")

        self._datasets[name] = dataframe.copy()
        return self._datasets[name]

    def load_csv(self, name, path, **kwargs):
        dataframe = load_csv_file(path, **kwargs)
        return self.add_data(name, dataframe)

    def get_data(self, name, *, copy=True):
        if name not in self._datasets:
            raise KeyError(f"Unknown dataset: {name}")

        dataframe = self._datasets[name]
        return dataframe.copy() if copy else dataframe

    def remove_data(self, name):
        if name not in self._datasets:
            raise KeyError(f"Unknown dataset: {name}")

        return self._datasets.pop(name)

    def list_datasets(self):
        return list(self._datasets.keys())

    def merge_data(self, names, new_name, *, replace=False):
        names = list(names)

        if not names:
            raise ValueError("At least one dataset is required")

        missing = [name for name in names if name not in self._datasets]
        if missing:
            raise KeyError(f"Unknown datasets: {missing}")

        merged = pd.concat(
            [self._datasets[name] for name in names],
            ignore_index=True,
            sort=False,
        )

        return self.add_data(new_name, merged, replace=replace)

    def export_csv(self, name, path, *, index=False, **kwargs):
        dataframe = self.get_data(name)
        path = Path(path)
        dataframe.to_csv(path, index=index, **kwargs)
        return path

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Dataset name must be a non-empty string")
        return name.strip()

    def __len__(self):
        return len(self._datasets)

    def __contains__(self, name):
        return name in self._datasets
