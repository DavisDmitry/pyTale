package dev.taledale.pytale;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.HostAccess;

public class PythonContextFactory {
    private PythonContextFactory() {}

    public static Context newContext() {
        return Context.newBuilder("python")
            .allowAllAccess(true)
            .allowHostAccess(HostAccess.ALL)
            .allowHostClassLookup(_ -> true)
            .option("engine.WarnInterpreterOnly", "false")
            .build();
    }
}
