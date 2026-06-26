package dev.taledale.pytale.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.Argument;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractAsyncPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.taledale.pytale.context.AsyncPythonContext;

import javax.annotation.Nonnull;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class PythonAsyncPlayerCommand extends AbstractAsyncPlayerCommand {
    private final int handlerIndex;
    private final Map<String, Argument<?, ?>> argumentMap;
    private final AsyncPythonContext asyncContext;

    public PythonAsyncPlayerCommand(
            @Nonnull String name,
            @Nonnull String description,
            int handlerIndex,
            @Nonnull Map<String, Argument<?, ?>> argumentMap,
            @Nonnull AsyncPythonContext asyncContext) {
        super(name, description);
        this.handlerIndex = handlerIndex;
        this.argumentMap = argumentMap;
        this.asyncContext = asyncContext;
    }

    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    @Nonnull
    @Override
    @SuppressWarnings("null")
    protected CompletableFuture<Void> executeAsync(
            @Nonnull CommandContext context,
            @Nonnull Store<EntityStore> store,
            @Nonnull Ref<EntityStore> ref,
            @Nonnull PlayerRef playerRef,
            @Nonnull World world) {
        PythonCommandContext pyCtx = new PythonCommandContext(context, argumentMap, world, playerRef);
        CompletableFuture<Void> future = new CompletableFuture<>();
        asyncContext.enqueueCommand(handlerIndex, pyCtx, future);
        return future;
    }
}
