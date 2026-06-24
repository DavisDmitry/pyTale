import re

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def camel_to_snake(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


_GETTER_PREFIXES = ("get", "is", "should", "can")


def java_getter_to_python_name(method_name: str) -> str:
    for prefix in _GETTER_PREFIXES:
        if method_name.startswith(prefix) and len(method_name) > len(prefix):
            rest = method_name[len(prefix) :]
            if not rest[0].isupper():
                continue
            snake = camel_to_snake(rest)
            if prefix == "get":
                return snake
            return f"{prefix}_{snake}"
    return camel_to_snake(method_name)


def extract_getter_stem(method_name: str) -> str | None:
    for prefix in _GETTER_PREFIXES:
        if method_name.startswith(prefix) and len(method_name) > len(prefix):
            rest = method_name[len(prefix) :]
            if rest[0].isupper():
                return rest
    return None


def extract_setter_stem(method_name: str) -> str | None:
    if method_name.startswith("set") and len(method_name) > 3:
        rest = method_name[3:]
        if rest[0].isupper():
            return rest
    return None


def java_class_to_python_name(java_fqn: str) -> tuple[str, ...]:
    simple = java_fqn.rsplit("/", 1)[-1]
    return tuple(simple.split("$"))
