package dev.taledale;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

import javax.annotation.Nonnull;

public class PyTale extends JavaPlugin {
    private static PyTale instance;

    public PyTale(@Nonnull JavaPluginInit init) {
        super(init);
    }

    public static PyTale get() {
        return instance;
    }
}
