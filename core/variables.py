class VariableStore:
    def __init__(self):
        self._values = {}

    def set(self, name, value):
        self._values[name] = value

    def get(self, name):
        return self._values[name]

    def has(self, name):
        return name in self._values

    def remove(self, name):
        self._values.pop(name, None)

    def clear(self):
        self._values.clear()

    def names(self):
        return tuple(self._values.keys())

    def as_dict(self):
        return dict(self._values)

    def update(self, values):
        self._values.update(values)

    def __contains__(self, name):
        return self.has(name)

    def __getitem__(self, name):
        return self.get(name)

    def __len__(self):
        return len(self._values)