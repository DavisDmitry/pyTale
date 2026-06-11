package dev.taledale.pytale.context;

import com.hypixel.hytale.logger.HytaleLogger;
import dev.taledale.pytale.AbstractPythonPlugin;
import dev.taledale.pytale.ExecutionContext;
import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Engine;
import org.graalvm.polyglot.HostAccess;
import org.graalvm.polyglot.PolyglotException;
import org.graalvm.polyglot.Value;

import java.util.List;

public class PythonContext {
    protected final AbstractPythonPlugin plugin;
    protected final HytaleLogger logger;
    protected final ExecutionContext executionContext;
    protected Context context;

    public PythonContext(
            AbstractPythonPlugin plugin,
            HytaleLogger logger,
            ExecutionContext executionContext) {
        this.plugin = plugin;
        this.logger = logger;
        this.executionContext = executionContext;
    }

    protected void buildContext() {
        this.context = Context.newBuilder("python")
                .engine(plugin.getPythonEngine())
                .allowAllAccess(true)
                .allowHostAccess(HostAccess.ALL)
                .allowHostClassLookup(_ -> true)
                .build();
    }

    protected void doInit() {
        List<String> wheelPaths = plugin.getWheelPaths();
        if (!wheelPaths.isEmpty()) {
            StringBuilder sb = new StringBuilder("import sys\n");
            for (String path : wheelPaths) {
                sb.append(String.format("sys.path.insert(0, '%s')\n", path));
            }
            context.eval("python", sb.toString());
        }

        Value bindings = context.getBindings("python");
        bindings.putMember("__identifier", plugin.getIdentifier());
        bindings.putMember("__manifest", plugin.getManifest());
        bindings.putMember("__data_directory", plugin.getDataDirectory());
        bindings.putMember("__context", executionContext.getValue());
        context.eval("python",
                "import pytale.plugin._plugin\n" +
                        "pytale.plugin._plugin._init_plugin" +
                        "(__identifier, __manifest, __data_directory, __context)");

        String moduleName = plugin.getManifest().getName().replace("-", "_");
        context.eval("python", "import " + moduleName);

        logger.atInfo().log("Python context initialized");
    }

    public void init() {
        try {
            buildContext();
            context.enter();
            doInit();
        } catch (PolyglotException e) {
            logger.atWarning().log("Python error during initialization: %s", e.getMessage());
        } catch (Exception e) {
            logger.atSevere().log("Failed to initialize context: %s", e.getMessage());
        } finally {
            context.leave();
        }
    }

    public Context getContext() {
        return context;
    }

    public void close() {
        close(false);
    }

    public void close(boolean cancelIfExecuting) {
        if (context != null) {
            try {
                context.close(cancelIfExecuting);
                logger.atInfo().log("Python context closed");
            } catch (Exception e) {
                logger.atSevere().log("Error closing context: %s", e.getMessage());
            }
        }
    }
}
