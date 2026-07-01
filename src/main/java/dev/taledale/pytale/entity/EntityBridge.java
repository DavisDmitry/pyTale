package dev.taledale.pytale.entity;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import javax.annotation.Nonnull;
import java.util.ArrayList;
import java.util.List;

/**
 * Static helpers for reading entities from a world's ECS store, called from Python via
 * {@code _java.type("dev.taledale.pytale.entity.EntityBridge")}.
 *
 * <p>There is no bulk "get all entity refs" method anywhere in the Hytale server API to
 * materialize as an array/collection (unlike {@link World#getPlayerRefs()}, which is scoped
 * to entities holding a {@code Player} component) — every existing usage of
 * {@code Store#forEachChunk} loops over {@code ArchetypeChunk#size()}/{@code getReferenceTo}
 * manually inside a lambda. This mirrors that idiom and returns a materialized list instead of
 * taking a Python callable, since pyTale has no existing convention for passing a Python
 * callable across the host-interop boundary as a Java functional interface.
 */
public final class EntityBridge {
    private EntityBridge() {
    }

    /**
     * Return every valid entity reference currently in {@code world}'s entity store.
     *
     * <p>Must be called on the world's own tick thread ({@link Store#forEachChunk} asserts
     * this internally and throws {@link IllegalStateException} otherwise); callers on the
     * Python side must guard with {@code World._require_thread} first.
     */
    @Nonnull
    public static List<Ref<EntityStore>> getAllRefs(@Nonnull World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> refs = new ArrayList<>(store.getEntityCount());
        store.forEachChunk((ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> commandBuffer) -> {
            for (int index = 0; index < chunk.size(); index++) {
                refs.add(chunk.getReferenceTo(index));
            }
        });
        return refs;
    }
}
