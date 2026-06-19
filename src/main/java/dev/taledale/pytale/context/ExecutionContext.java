package dev.taledale.pytale.context;

/**
 * Execution context for Python code in pyTale plugins.
 * Must match pytale.plugin.ExecutionContext values.
 */
public enum ExecutionContext {
    GENERAL(0),
    WORLD(1);

    private final int value;

    ExecutionContext(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }
}
