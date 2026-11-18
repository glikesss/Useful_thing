from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Curve:
    """A curve defined by two columns of an experimental DataFrame."""

    data: pd.DataFrame
    x_column: str
    y_column: str
    label: str | None = None
    style: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        for column in (self.x_column, self.y_column):
            if column not in self.data.columns:
                raise KeyError(f"Unknown column: {column}")

        if self.label is not None and not isinstance(self.label, str):
            raise TypeError("label must be a string or None")

        if not isinstance(self.style, dict):
            raise TypeError("style must be a dictionary")

        self.data = self.data.copy(deep=True)
        self.style = dict(self.style)

    def get_values(self):
        def convert(column):
            values = (
                self.data[column]
                .astype("string")
                .str.strip()
                .str.replace(",", ".", regex=False)
                .str.replace("−", "-", regex=False)
                .str.casefold()
                .replace({
                    "": pd.NA,
                    "бесконечность": float("inf"),
                    "+бесконечность": float("inf"),
                    "infinity": float("inf"),
                    "+infinity": float("inf"),
                    "∞": float("inf"),
                    "+∞": float("inf"),
                    "-бесконечность": float("-inf"),
                    "-infinity": float("-inf"),
                    "-∞": float("-inf"),
                })
            )
            return pd.to_numeric(
                values, errors="raise"
            ).to_numpy(dtype=float, na_value=float("nan"))

        x = convert(self.x_column)
        y = convert(self.y_column)

        return x, y

    def plot(self, axes):
        x, y = self.get_values()
        kwargs = dict(self.style)

        if self.label is not None:
            kwargs.setdefault("label", self.label)

        return axes.plot(x, y, **kwargs)[0]

