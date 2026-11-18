from .errors import DependencyError


def topological_sort(graph):
    """
    graph:
        {
            "a": {"b", "c"},
            "b": {"c"},
            "c": set()
        }

    Значение каждого узла — его зависимости.
    """

    result = []
    temporary = set()
    permanent = set()

    def visit(node):
        if node in permanent:
            return

        if node in temporary:
            raise DependencyError(
                f"Обнаружена циклическая зависимость: {node}"
            )

        temporary.add(node)

        for dependency in graph.get(node, set()):
            if dependency in graph:
                visit(dependency)

        temporary.remove(node)
        permanent.add(node)
        result.append(node)

    for node in graph:
        visit(node)

    return result