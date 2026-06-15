package dev.taledale.pytale.context.world;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.taledale.pytale.AbstractPythonPlugin;
import dev.taledale.pytale.ExecutionContext;
import dev.taledale.pytale.context.PythonContext;

public class WorldPythonContext extends PythonContext {
    private final World world;

    public WorldPythonContext(AbstractPythonPlugin plugin, World world) {
        super(
                plugin,
                plugin.getLogger().getSubLogger("[" + world.getName() + "]"),
                ExecutionContext.WORLD);
        this.world = world;
    }

    @Override
    public void init() {
        world.execute(() -> super.init());
    }

    public void eval(String code) {
        world.execute(() -> {
            if (context == null) {
                logger.atWarning().log("Context not initialized, cannot eval");
                return;
            }
            withContext(() -> context.eval("python", code));
        });
    }

    public World getWorld() {
        return world;
    }
}
