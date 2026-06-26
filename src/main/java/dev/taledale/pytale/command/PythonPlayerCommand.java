package dev.taledale.pytale.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.Argument;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.taledale.pytale.context.world.WorldContextManager;
import dev.taledale.pytale.context.world.WorldPythonContext;

import javax.annotation.Nonnull;
import java.util.Map;

public class PythonPlayerCommand extends AbstractPlayerCommand {
    private final int handlerIndex;
    private final Map<String, Argument<?, ?>> argumentMap;
    private final WorldContextManager worldContextManager;

    public PythonPlayerCommand(
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
    protected void execute(
            @Nonnull CommandContext context,
            @Nonnull Store<EntityStore> store,
            @Nonnull Ref<EntityStore> ref,
            @Nonnull PlayerRef playerRef,
            @Nonnull World world) {
        WorldPythonContext worldCtx = worldContextManager.getContext(world);
        if (worldCtx == null) return;
        PythonCommandContext pyCtx = new PythonCommandContext(context, argumentMap, world, playerRef);
        worldCtx.invokeCommandHandler(handlerIndex, pyCtx);
    }
}
