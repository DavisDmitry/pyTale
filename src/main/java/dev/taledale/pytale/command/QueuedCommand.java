package dev.taledale.pytale.command;

import java.util.concurrent.CompletableFuture;

/**
 * A command queued for processing by the async Python event loop.
 *
 * <p>A poison pill (signalling shutdown) is represented by an {@code index < 0} with
 * {@code null} ctx and future.
 */
public record QueuedCommand(
        int index,
        PythonCommandContext ctx,
        CompletableFuture<Void> future) {
}
