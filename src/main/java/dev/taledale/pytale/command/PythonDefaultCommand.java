package dev.taledale.pytale.command;

import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.Argument;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractAsyncCommand;
import dev.taledale.pytale.context.AsyncPythonContext;

import javax.annotation.Nonnull;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class PythonDefaultCommand extends AbstractAsyncCommand {
    private final int handlerIndex;
    private final Map<String, Argument<?, ?>> argumentMap;
    private final AsyncPythonContext asyncContext;

    public PythonDefaultCommand(
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
    protected CompletableFuture<Void> executeAsync(@Nonnull CommandContext context) {
        PythonCommandContext pyCtx = new PythonCommandContext(context, argumentMap, null, null);
        CompletableFuture<Void> future = new CompletableFuture<>();
        asyncContext.enqueueCommand(handlerIndex, pyCtx, future);
        return future;
    }
}
