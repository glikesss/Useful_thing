from pathlib import Path

import matplotlib.pyplot as plt

from plotting.curves import Curve


class PlotManager:
    """Manage experimental curves on a Matplotlib figure."""

    def __init__(
        self,
        *,
        title="",
        xlabel="",
        ylabel="",
        figsize=(8, 5),
        grid=True,
    ):
        self._title = title
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._grid = grid

        self.figure, self.axes = plt.subplots(figsize=figsize)
        self._curves = []
        self._lines = []

        self._configure_axes()

    def _configure_axes(self):
        self.axes.set_title(self._title)
        self.axes.set_xlabel(self._xlabel)
        self.axes.set_ylabel(self._ylabel)
        self.axes.grid(self._grid)

    @property
    def curves(self):
        return tuple(self._curves)

    def add_curve(
        self,
        data,
        x_column=None,
        y_column=None,
        *,
        label=None,
        **style,
    ):
        if isinstance(data, Curve):
            if (
                x_column is not None
                or y_column is not None
                or label is not None
                or style
            ):
                raise ValueError(
                    "Curve options must be defined in the Curve object"
                )
            curve = data
        else:
            if x_column is None or y_column is None:
                raise ValueError(
                    "x_column and y_column are required"
                )

            curve = Curve(
                data=data,
                x_column=x_column,
                y_column=y_column,
                label=label,
                style=style,
            )

        line = curve.plot(self.axes)

        self._curves.append(curve)
        self._lines.append(line)
        self._refresh_legend()

        return line

    def add_experiment(
        self,
        experiment,
        x_column,
        y_column,
        *,
        label=None,
        **style,
    ):
        if not hasattr(experiment, "get_data"):
            raise TypeError("experiment must provide get_data()")

        if label is None:
            label = getattr(experiment, "name", None)

        return self.add_curve(
            experiment.get_data(),
            x_column,
            y_column,
            label=label,
            **style,
        )

    def remove_curve(self, index):
        if not isinstance(index, int):
            raise TypeError("index must be an integer")

        if index < -len(self._curves) or index >= len(self._curves):
            raise IndexError("Curve index out of range")

        curve = self._curves.pop(index)
        line = self._lines.pop(index)
        line.remove()

        self._refresh_legend()
        return curve

    def _refresh_legend(self):
        handles, labels = self.axes.get_legend_handles_labels()

        legend = self.axes.get_legend()

        if labels:
            self.axes.legend()
        elif legend is not None:
            legend.remove()

    def clear(self):
        self.axes.clear()
        self._curves.clear()
        self._lines.clear()
        self._configure_axes()

    def set_title(self, title):
        self._title = title
        self.axes.set_title(title)

    def set_labels(self, *, xlabel=None, ylabel=None):
        if xlabel is not None:
            self._xlabel = xlabel
            self.axes.set_xlabel(xlabel)

        if ylabel is not None:
            self._ylabel = ylabel
            self.axes.set_ylabel(ylabel)

    def save(self, path, *, dpi=150, **kwargs):
        path = Path(path)
        self.figure.savefig(path, dpi=dpi, **kwargs)
        return path

    def show(self):
        plt.show()

    def close(self):
        plt.close(self.figure)
