package dev.taledale;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

import javax.annotation.Nonnull;

public class PyTale extends JavaPlugin {
    private static PyTale instance;
    private SingleThreadPythonRuntime runtime;
    private PluginManager pluginManager;
    private WorldContextManager worldContextManager;

    public PyTale(@Nonnull JavaPluginInit init) {
        super(init);
    }

    public static PyTale get() {
        return instance;
    }

    @Override
    protected void setup() {
        instance = this;
        getLogger().atInfo().log("PyTale setup started");

        // 1. Initialize runtime and load plugins with their general contexts
        runtime = new SingleThreadPythonRuntime();
        pluginManager = new PluginManager();
        pluginManager.loadAllPlugins();

        // 2. Initialize scheduler contexts for each plugin
        pluginManager.initializeSchedulerContexts();

        // 3. Initialize world contexts
        worldContextManager = new WorldContextManager(getEventRegistry());
        worldContextManager.start();

        getLogger().atInfo().log("PyTale setup completed");
    }

    @Override
    protected void shutdown() {
        getLogger().atInfo().log("PyTale shutdown started");
        if (worldContextManager != null) {
            worldContextManager.shutdown();
        }
        if (pluginManager != null) {
            pluginManager.shutdown();
        }
        getLogger().atInfo().log("PyTale shutdown completed");
    }

    public SingleThreadPythonRuntime getRuntime() {
        return runtime;
    }

    public PluginManager getPluginManager() {
        return pluginManager;
    }

    public WorldContextManager getWorldContextManager() {
        return worldContextManager;
    }
}
