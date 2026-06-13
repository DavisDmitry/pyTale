from typing import Any, TypeGuard, final

@final
class JavaClass:
    """A Java class or interface, as returned by ``java.type()``.

    Callable to create instances; static members are accessible as attributes.

    .. note::
        This class exists only at type-checking time and cannot be imported at
        runtime. Use a ``TYPE_CHECKING`` guard when you need it in annotations::

            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                from java import JavaClass
    """

    def __call__(self, *args: Any, **kwargs: Any) -> JavaObject: ...
    def __getattr__(self, name: str) -> Any: ...

@final
class JavaObject:
    """An instance of a Java object.

    .. note::
        This class exists only at type-checking time and cannot be imported at
        runtime. Use a ``TYPE_CHECKING`` guard when you need it in annotations::

            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                from java import JavaObject
    """

    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

def __getattr__(name: str) -> Any: ...
def type(name: str) -> JavaClass:
    """Look up a Java class by its fully qualified name.

    Example::

        ArrayList = java.type("java.util.ArrayList")
        lst = ArrayList()
    """
    ...

def add_to_classpath(*paths: str) -> None:
    """Add one or more paths (JAR files or directories) to the host class path."""
    ...

def is_function(object: Any) -> bool:
    """Return True if *object* is a Java host function or method."""
    ...

def is_object(object: Any) -> bool:
    """Return True if *object* is any Java host object (instance or class)."""
    ...

def is_symbol(object: Any) -> TypeGuard[JavaClass]:
    """Return True if *object* is a Java host symbol (i.e. a class handle)."""
    ...

def is_type(object: Any) -> TypeGuard[JavaClass]:
    """Return True if *object* is a Java host object that is an instance of ``java.lang.Class``."""
    ...

def instanceof(object: Any, klass: JavaClass) -> bool:
    """Return True if *object* is an instance of the Java class *klass*.

    Example::

        ArrayList = java.type("java.util.ArrayList")
        java.instanceof(lst, ArrayList)
    """
    ...

def as_java_byte_array(object: bytes | bytearray | memoryview) -> JavaObject:
    """Wrap a Python bytes-like object as a Java ``byte[]``."""
    ...
