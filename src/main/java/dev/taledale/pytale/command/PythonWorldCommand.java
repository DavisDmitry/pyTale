package dev.taledale.pytale.command;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.Argument;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractWorldCommand;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.taledale.pytale.context.world.WorldContextManager;
import dev.taledale.pytale.context.world.WorldPythonContext;

import javax.annotation.Nonnull;
import java.util.Map;

public class PythonWorldCommand extends AbstractWorldCommand {
    private final int handlerIndex;
    private final Map<String, Argument<?, ?>> argumentMap;
    private final WorldContextManager worldContextManager;

    public PythonWorldCommand(
            @Nonnull String name,
            @Nonnull String description,
            int handlerIndex,
            @Nonnull Map<String, Argument<?, ?>> argumentMap,
            @Nonnull WorldContextManager worldContextManager) {
        super(name, description);
        this.handlerIndex = handlerIndex;
        this.argumentMap = argumentMap;
        this.worldContextManager = worldContextManager;
    }

    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    @Override
    @SuppressWarnings("null")
    protected void execute(@Nonnull CommandContext context, @Nonnull World world, @Nonnull Store<EntityStore> store) {
        WorldPythonContext worldCtx = worldContextManager.getContext(world);
        if (worldCtx == null) return;
        PythonCommandContext pyCtx = new PythonCommandContext(context, argumentMap, world, null);
        worldCtx.invokeCommandHandler(handlerIndex, pyCtx);
    }
}
