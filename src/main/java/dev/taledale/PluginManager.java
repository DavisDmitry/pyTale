package dev.taledale;

import com.hypixel.hytale.logger.HytaleLogger;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Stream;

public class PluginManager {
    private final List<PyPlugin> plugins = new CopyOnWriteArrayList<>();
    private final HytaleLogger logger;

    public PluginManager() {
        this.logger = PyTale.get().getLogger().getSubLogger("PluginManager");
    }

    public void loadAllPlugins() {
        try {
            Path pluginsDir = PyTale.get().getDataDirectory().resolve("plugins");
            if (!Files.exists(pluginsDir)) {
                Files.createDirectories(pluginsDir);
                logger.atInfo().log("Plugins directory created: %s", pluginsDir);
                return;
            }

            logger.atInfo().log("Scanning plugins directory: %s", pluginsDir);
            try (Stream<Path> files = Files.list(pluginsDir)) {
                files.filter(p -> p.toString().endsWith(".py"))
                    .forEach(this::loadPlugin);
            }

            logger.atInfo().log("Loaded %d plugin(s)", plugins.size());
        } catch (IOException e) {
            logger.atSevere().log("Error loading plugins: %s", e.getMessage());
        }
    }

    private void loadPlugin(Path pluginPath) {
        try {
            String pluginName = pluginPath.getFileName().toString();
            if (pluginName.endsWith(".py")) {
                pluginName = pluginName.substring(0, pluginName.length() - 3);
            }

            logger.atInfo().log("Loading plugin: %s", pluginName);
            String code = Files.readString(pluginPath);

            PyPlugin plugin = new PyPlugin(pluginName, code);
            plugin.initializeGeneralContext();
            plugins.add(plugin);

            logger.atInfo().log("Loaded plugin: %s", pluginName);
        } catch (Exception e) {
            logger.atWarning().log("Error loading plugin %s: %s", pluginPath.getFileName(), e.getMessage());
        }
    }

    public List<PyPlugin> getPlugins() {
        return List.copyOf(plugins);
    }

    public PyPlugin getPlugin(String name) {
        return plugins.stream()
            .filter(p -> p.getName().equals(name))
            .findFirst()
            .orElse(null);
    }

    public void initializeSchedulerContexts() {
        logger.atInfo().log("Initializing scheduler contexts for %d plugin(s)", plugins.size());
        for (PyPlugin plugin : plugins) {
            plugin.initializeSchedulerContext();
        }
    }

    public void shutdown() {
        logger.atInfo().log("Shutting down plugin manager");
        for (PyPlugin plugin : plugins) {
            plugin.close();
        }
        plugins.clear();
    }
}
