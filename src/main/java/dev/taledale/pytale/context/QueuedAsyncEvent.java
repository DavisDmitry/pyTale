package dev.taledale.pytale.context;

import com.hypixel.hytale.event.IAsyncEvent;

import java.util.concurrent.CompletableFuture;

/**
 * An async event queued for processing by the {@link AsyncPythonContext} event loop.
 *
 * <p>A poison pill (signalling shutdown) is represented by an {@code index < 0} with
 * {@code null} event and future.
 */
public record QueuedAsyncEvent(
        int index,
        IAsyncEvent<?> event,
        CompletableFuture<IAsyncEvent<?>> future) {
}
