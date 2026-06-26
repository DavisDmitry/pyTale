package dev.taledale.pytale.command;

import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.CommandSender;
import com.hypixel.hytale.server.core.command.system.arguments.system.Argument;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import java.util.Map;

/**
 * Wraps a {@link CommandContext} with a name-to-{@link Argument} map so Python can
 * look up arguments by string name. Also carries optional world/player references
 * populated by the specific command type.
 */
public class PythonCommandContext {
    private final CommandContext context;
    private final Map<String, Argument<?, ?>> arguments;
    private final World world;
    private final PlayerRef playerRef;

    public PythonCommandContext(
            @Nonnull CommandContext context,
            @Nonnull Map<String, Argument<?, ?>> arguments,
            @Nullable World world,
            @Nullable PlayerRef playerRef) {
        this.context = context;
        this.arguments = arguments;
        this.world = world;
        this.playerRef = playerRef;
    }

    @Nonnull
    public CommandSender sender() {
        return context.sender();
    }

    public boolean isPlayer() {
        return context.isPlayer();
    }

    @Nullable
    public World getWorld() {
        return world;
    }

    @Nullable
    public PlayerRef getPlayerRef() {
        return playerRef;
    }

    @Nullable
    public Object get(@Nonnull String name) {
        Argument<?, ?> arg = arguments.get(name);
        if (arg == null) {
            throw new IllegalArgumentException("Unknown argument: " + name);
        }
        return context.get(arg);
    }

    public boolean provided(@Nonnull String name) {
        Argument<?, ?> arg = arguments.get(name);
        if (arg == null) {
            throw new IllegalArgumentException("Unknown argument: " + name);
        }
        return context.provided(arg);
    }
}
