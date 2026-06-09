package dev.taledale.pytale;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.PolyglotException;

import javax.annotation.Nonnull;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public abstract class AbstractPythonPlugin extends JavaPlugin {
    private final AtomicReference<Context> generalContext = new AtomicReference<>();
    private PluginSchedulerContext schedulerContext;
    private SingleThreadPythonRuntime runtime;
    private WorldContextManager worldContextManager;

    public AbstractPythonPlugin(@Nonnull JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        try {
            runtime = new SingleThreadPythonRuntime();
            schedulerContext = new PluginSchedulerContext(this);
            worldContextManager = new WorldContextManager(this);

            initializeGeneralContext();
            initializeSchedulerContext();
            worldContextManager.start();
        } catch (Exception e) {
            getLogger().atSevere().log("Failed to load Python plugin: %s", e.getMessage());
        }
    }

    @Override
    protected void shutdown() {
        Context ctx = generalContext.get();
        if (ctx != null) {
            try {
                ctx.close();
                getLogger().atInfo().log("General Python context closed");
            } catch (Exception e) {
                getLogger().atSevere().log("Error closing context: %s", e.getMessage());
            }
        }
        if (schedulerContext != null) {
            schedulerContext.close();
        }
        if (worldContextManager != null) {
            worldContextManager.shutdown();
        }
    }

    private void initializeGeneralContext() {
        CountDownLatch latch = new CountDownLatch(1);

        runtime.submit(() -> {
            ClassLoader previousCl = Thread.currentThread().getContextClassLoader();
            try {
                Thread.currentThread().setContextClassLoader(PyTale.get().getClass().getClassLoader());
                Context ctx = PythonContextFactory.newContext();
                generalContext.set(ctx);
                getLogger().atInfo().log("General Python context initialized");

                String pythonCode = loadPythonCode();
                ctx.eval("python", pythonCode);
                getLogger().atInfo().log("Plugin code executed");
            } catch (PolyglotException e) {
                getLogger().atWarning().log("Python error during initialization: %s", e.getMessage());
            } catch (Exception e) {
                getLogger().atWarning().log("Error executing plugin: %s", e.getMessage());
            } finally {
                Thread.currentThread().setContextClassLoader(previousCl);
                latch.countDown();
            }
        });

        try {
            if (!latch.await(5, TimeUnit.SECONDS)) {
                getLogger().atWarning().log("General context initialization timed out");
            }
        } catch (InterruptedException e) {
            getLogger().atWarning().log("General context initialization interrupted");
            Thread.currentThread().interrupt();
        }
    }

    protected String loadPythonCode() throws Exception {
        String moduleName = getPythonModuleName();
        String entryPath = "python/" + moduleName + "/__init__.py";

        java.nio.file.Path location = getPluginJarPath();

        try (java.util.zip.ZipFile zf = new java.util.zip.ZipFile(location.toFile())) {
            java.util.zip.ZipEntry entry = zf.getEntry(entryPath);
            if (entry == null) {
                throw new Exception("Python code not found in plugin: " + entryPath);
            }
            try (java.io.InputStream is = zf.getInputStream(entry)) {
                return new String(is.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
            }
        }
    }

    private java.nio.file.Path getPluginJarPath() throws Exception {
        java.nio.file.Path pluginFile = getFile();
        if (pluginFile == null || !java.nio.file.Files.exists(pluginFile)) {
            throw new Exception("Cannot determine plugin location");
        }
        return pluginFile;

    }

    private String getPythonModuleName() throws Exception {
        String name = getManifest().getName();
        return name.replace("-", "_");
    }

    private void initializeSchedulerContext() {
        schedulerContext.initialize();
    }

    public Context getGeneralContext() {
        return generalContext.get();
    }

    public PluginSchedulerContext getSchedulerContext() {
        return schedulerContext;
    }
}
