package dev.taledale.pytale.command;

import com.hypixel.hytale.server.core.command.system.basecommands.AbstractCommandCollection;

import javax.annotation.Nonnull;

public class PythonCommandCollection extends AbstractCommandCollection {
    public PythonCommandCollection(@Nonnull String name, @Nonnull String description) {
        super(name, description);
    }

    @Override
    protected boolean canGeneratePermission() {
        return false;
    }
}
