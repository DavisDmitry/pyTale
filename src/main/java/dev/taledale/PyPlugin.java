package dev.taledale;

import com.hypixel.hytale.logger.HytaleLogger;
import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.PolyglotException;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class PyPlugin {
    private final String name;
    private final String code;
    private final AtomicReference<Context> generalContext = new AtomicReference<>();
    private final PluginSchedulerContext schedulerContext;
    private final HytaleLogger logger;

    public PyPlugin(String name, String code) {
        this.name = name;
        this.code = code;
        this.logger = PyTale.get().getLogger().getSubLogger("[" + name + "]");
        this.schedulerContext = new PluginSchedulerContext(this);
    }

    public void initializeGeneralContext() {
        CountDownLatch latch = new CountDownLatch(1);

        // Инициализируем контекст на SingleThreadPythonRuntime
        SingleThreadPythonRuntime runtime = PyTale.get().getRuntime();
        runtime.submit(() -> {
            ClassLoader previousCl = Thread.currentThread().getContextClassLoader();
            try {
                Thread.currentThread().setContextClassLoader(PyTale.get().getClass().getClassLoader());
                Context ctx = PythonContextFactory.newContext();
                generalContext.set(ctx);
                logger.atInfo().log("General Python context initialized");

                // Выполняем код плагина в его контексте
                ctx.eval("python", code);
                logger.atInfo().log("Plugin code executed");
            } catch (PolyglotException e) {
                logger.atWarning().log("Python error during initialization: %s", e.getMessage());
            } finally {
                Thread.currentThread().setContextClassLoader(previousCl);
                latch.countDown();
            }
        });

        try {
            if (!latch.await(5, TimeUnit.SECONDS)) {
                logger.atWarning().log("General context initialization timed out");
            }
        } catch (InterruptedException e) {
            logger.atWarning().log("General context initialization interrupted");
            Thread.currentThread().interrupt();
        }
    }

    public void initializeSchedulerContext() {
        schedulerContext.initialize();
    }

    public String getName() {
        return name;
    }

    public Context getGeneralContext() {
        return generalContext.get();
    }

    public PluginSchedulerContext getSchedulerContext() {
        return schedulerContext;
    }

    public void close() {
        Context ctx = generalContext.get();
        if (ctx != null) {
            try {
                ctx.close();
                logger.atInfo().log("General Python context closed");
            } catch (Exception e) {
                logger.atSevere().log("Error closing context: %s", e.getMessage());
            }
        }
        schedulerContext.close();
    }
}
