# Hytale Events — Threading Analysis

Analysis of all Hytale server events: dispatch mechanism, execution thread, cancellability.

## Legend

| Term | Meaning |
|---|---|
| **IEvent** | Synchronous event — handlers run on the dispatching thread before control returns |
| **IAsyncEvent** | Asynchronous event — handlers receive a `CompletableFuture` |
| **EcsEvent** | Dispatched via `store.invoke()` / `commandBuffer.invoke()`, not via `EventBus` |
| **GlobalEventBus** | Dispatched via `HytaleServer.get().getEventBus().dispatch()` |
| **WorldThread** | The `TickingThread` owned by a specific `World` instance |
| **Netty** | Netty I/O EventLoop thread (network layer) |
| **FJP** | `ForkJoinPool.commonPool()` — used by `CompletableFuture` without an explicit executor |
| **main** | Server startup / shutdown thread |

---

## Lifecycle / System Events

| Event | Type | Cancellable | Mechanism | Thread | Notes |
|---|---|---|---|---|---|
| `BootEvent` | IEvent | no | GlobalEventBus | main | Fired in `HytaleServer` after startup |
| `ShutdownEvent` | IEvent | no | GlobalEventBus | main | Fired in `HytaleServer.shutdown0()` |
| `PrepareUniverseEvent` | IEvent | no | GlobalEventBus | main | `Universe.init()` — `@Deprecated` |
| `AllWorldsLoadedEvent` | IEvent | no | GlobalEventBus | main / FJP | 2 fire sites: one bare, one in `thenRun()` |
| `PluginEvent` | IEvent | no | GlobalEventBus | setup | Abstract base class |
| `PluginSetupEvent` | IEvent | no | GlobalEventBus | setup | `PluginManager` — fired on plugin registration |

---

## Player Events (GlobalEventBus)

| Event | Type | Cancellable | Mechanism | Thread | Notes |
|---|---|---|---|---|---|
| `PlayerEvent<K>` | IEvent | no | — | — | Abstract base class |
| `PlayerRefEvent<K>` | IEvent | no | — | — | Abstract base class |
| `PlayerSetupConnectEvent` | IEvent | **yes** | GlobalEventBus | **Netty** | `SetupPacketHandler.registered0()` — can `referToServer()` |
| `PlayerSetupDisconnectEvent` | IEvent | no | GlobalEventBus | **Netty** | Fired before player enters any world |
| `PlayerConnectEvent` | IEvent | no | GlobalEventBus | **FJP** | `Universe.addPlayer()` — in CompletableFuture chain; can `setWorld()` |
| `PlayerDisconnectEvent` | IEvent | no | GlobalEventBus | **varies** | `Universe.removePlayer()` — called from different contexts |
| `AddPlayerToWorldEvent` | IEvent | no | GlobalEventBus | **FJP** | `World.addPlayer()` — outside `world.execute()`; can modify `joinMessage` |
| `RemovedPlayerFromWorldEvent` | IEvent | no | GlobalEventBus | WorldThread | `PlayerSystems.PlayerRemovedSystem.onEntityRemoved()` |
| `DrainPlayerFromWorldEvent` | IEvent | no | GlobalEventBus | WorldThread / FJP | `World.drainPlayersTo()` — during world shutdown; can `setWorld()` / `setTransform()` |
| `PlayerReadyEvent` | IEvent | no | GlobalEventBus | WorldThread | `Player.handleClientReady()` → `world.execute()` from ScheduledExecutor |
| `PlayerChatEvent` | **IAsyncEvent** | **yes** | GlobalEventBus (async) | Netty (dispatch) / FJP (handlers) | `GamePacketHandler` → `dispatchForAsync()` → CompletableFuture; can modify content / targets / formatter |
| `PlayerMouseButtonEvent` | IEvent | **yes** | GlobalEventBus | WorldThread | `InteractionModule` — in entity tick packet processing |
| `PlayerMouseMotionEvent` | IEvent | **yes** | GlobalEventBus | WorldThread | Same as `PlayerMouseButtonEvent` |
| `PlayerInteractEvent` | IEvent | **yes** | GlobalEventBus | WorldThread | `@Deprecated` — do not use in new code |
| `PlayerCraftEvent` | IEvent | no | GlobalEventBus | WorldThread | `@Deprecated(forRemoval = true)` |

---

## World / Chunk Events (GlobalEventBus)

| Event | Type | Cancellable | Mechanism | Thread | Notes |
|---|---|---|---|---|---|
| `WorldEvent` | IEvent | no | — | — | Abstract base class |
| `AddWorldEvent` | IEvent | **yes** | GlobalEventBus | **FJP** | `Universe.makeWorld()` → `CompletableFuture.supplyAsync()` without explicit executor |
| `RemoveWorldEvent` | IEvent | **yes** | GlobalEventBus | main / WorldThread | `Universe.removeWorld()` — multiple call sites; exceptional removal cannot be cancelled |
| `StartWorldEvent` | IEvent | no | GlobalEventBus | WorldThread | `World.onStart()` — part of `TickingThread` startup |
| `WorldGenChunksClearedEvent` | IEvent | no | GlobalEventBus | FJP | `WorldGenReloadCommand` → `thenComposeAsync` without executor |
| `ChunkEvent` | IEvent | no | — | — | Abstract base class |
| `ChunkPreLoadProcessEvent` | IEvent | no | GlobalEventBus | WorldThread | `ChunkStore.postLoadChunk()` — `debugAssertInTickingThread()`; keep handlers fast (warning if > TICK_STEP) |

---

## ECS Chunk Events

Dispatched via `store.invoke()` / `commandBuffer.invoke()`. All run on **WorldThread**.

| Event | Cancellable | Notes |
|---|---|---|
| `ChunkSaveEvent` | **yes** | `ChunkSavingSystems.tryQueue/tryQueueSync` — during tick |
| `ChunkUnloadEvent` | **yes** | `ChunkUnloadingSystem` — can prevent unload |
| `MoonPhaseChangeEvent` | no | `WorldTimeResource.setMoonPhase()` → `componentAccessor.invoke(event)` |

---

## ECS Interaction Events

Dispatched via `store.invoke()` / `commandBuffer.invoke()`. All run on **WorldThread**.

| Event | Cancellable | Notes |
|---|---|---|
| `PlaceBlockEvent` | **yes** | `BlockPlaceUtils` → `entityStore.invoke(ref, event)` |
| `BreakBlockEvent` | **yes** | `BlockHarvestUtils` → `entityStore.invoke(ref, event)` and world-wide invoke |
| `DamageBlockEvent` | **yes** | `BlockHarvestUtils` → `entityStore.invoke(ref, event)` |
| `UseBlockEvent.Pre` | **yes** | `UseBlockInteraction` → `commandBuffer.invoke(ref, event)` |
| `UseBlockEvent.Post` | no | `UseBlockInteraction` → `commandBuffer.invoke(ref, event)` |
| `LivingEntityUseBlockEvent` | no | GlobalEventBus, WorldThread — `@Deprecated(forRemoval = true)` |
| `ChangeGameModeEvent` | **yes** | `Player.setGameMode()` → `componentAccessor.invoke(ref, event)` |
| `BreathingCheckEvent` | no | `EntityUtils` → `componentAccessor.invoke(ref, event)`; can flip `canBreathe` |
| `DiscoverZoneEvent.Display` | **yes** | `WorldMapTracker` → `componentAccessor.invoke(ref, event)` |

---

## ECS Inventory Events

All run on **WorldThread**.

| Event | Cancellable | Notes |
|---|---|---|
| `DropItemEvent.PlayerRequest` | **yes** | `InventoryPacketHandler` → `world.execute(() -> store.invoke(ref, event))` |
| `DropItemEvent.Drop` | **yes** | `ItemUtils.throwItem()` → `componentAccessor.invoke(ref, event)` |
| `InteractivelyPickupItemEvent` | **yes** | `ItemUtils.interactivelyPickupItem()` → `componentAccessor.invoke(ref, event)` |
| `InventoryChangeEvent` | no | `InventorySystems.InventoryChangeEventSystem` — EntityTickingSystem |
| `InventoryActiveSlotRequestEvent` | **yes** | `InventoryPacketHandler` → `world.execute(() -> store.invoke(ref, event))` |
| `InventorySetActiveSlotEvent` | no | `ActiveSlotInventoryComponent` → `componentAccessor.invoke(...)` |
| `CraftRecipeEvent.Pre` | **yes** | `CraftingManager` → `store.invoke()` |
| `CraftRecipeEvent.Post` | **yes** | `CraftingManager` → `store.invoke()` |

---

## ECS Damage / Death Events

All run on **WorldThread**.

| Event | Cancellable | Notes |
|---|---|---|
| `KillFeedEvent.KillerMessage` | **yes** | `DeathSystems.KillFeed` → `store.invoke(sourceRef, event)` |
| `KillFeedEvent.DecedentMessage` | **yes** | `DeathSystems.KillFeed` → `store.invoke(ref, event)` |
| `KillFeedEvent.Display` | **yes** | `DeathSystems.KillFeed` → `store.invoke(ref, event)`; can modify targets and icon |

---

## Entity Events (GlobalEventBus)

| Event | Type | Cancellable | Mechanism | Thread | Notes |
|---|---|---|---|---|---|
| `EntityEvent<E, K>` | IEvent | no | — | — | Abstract base class |
| `EntityRemoveEvent` | IEvent | no | GlobalEventBus | WorldThread | `Entity.remove()` — `debugAssertInTickingThread()` |

---

## Prefab Events (ECS, WorldThread)

| Event | Cancellable | Notes |
|---|---|---|
| `PrefabPasteEvent` | **yes** | `PrefabUtil` → `componentAccessor.invoke(event)` (world-wide) |
| `PrefabPlaceEntityEvent` | **yes** | `PrefabUtil` → `store.invoke()` |

---

## Permissions Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `GroupPermissionChangeEvent.Added` | IEvent | no | **unknown** | Called from `PermissionsModule` API methods without thread guarantee |
| `GroupPermissionChangeEvent.Removed` | IEvent | no | **unknown** | Same |
| `PlayerPermissionChangeEvent.PermissionsAdded` | IEvent | no | **unknown** | Same |
| `PlayerPermissionChangeEvent.PermissionsRemoved` | IEvent | no | **unknown** | Same |
| `PlayerGroupEvent.Added` | IEvent | no | **unknown** | Extends `PlayerPermissionChangeEvent` |
| `PlayerGroupEvent.Removed` | IEvent | no | **unknown** | Extends `PlayerPermissionChangeEvent` |

---

## Builtin Events

| Event | Type | Cancellable | Mechanism | Thread | Notes |
|---|---|---|---|---|---|
| `TriggerVolumeEvent` | IEvent | no | GlobalEventBus | WorldThread | `TriggerVolumeTickingSystem` |
| `DiscoverInstanceEvent.Display` | EcsEvent | **yes** | ECS | WorldThread | `InstancesPlugin` → `store.invoke(ref, event)` |
| `TreasureChestOpeningEvent` | IEvent | no | GlobalEventBus | WorldThread | `TreasureChestBlock` → fired inside block handler |
| `ModifyWarpEvent` | IEvent | **yes** | GlobalEventBus | — | Abstract base class for warp modification events |
| `RemoveWarpEvent` | IEvent | **yes** | GlobalEventBus | command thread | `WarpRemoveCommand` → `CommandBase.executeSync` |
| `ReplaceWarpEvent` | IEvent | **yes** | GlobalEventBus | FJP | `WarpSetCommand` → `AbstractPlayerCommand` → `AbstractAsyncCommand` |

---

## ECS Block Events

Dispatched via `store.invoke()`. All run on **WorldThread**.

| Event | Cancellable | Notes |
|---|---|---|
| `BlockReplaceEvent` | no | `BlockEntity` — fires when a block entity is replaced in-place; used internally by `ItemContainerSystems` |

---

## World Path Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `WorldPathChangedEvent` | IEvent | no | FJP | `WorldPathConfig.setPath()` — called from `AbstractPlayerCommand` (async) path commands |

---

## NPC Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `AllNPCsLoadedEvent` | IEvent | no | setup/main | `BuilderManager.onAllBuildersLoaded()` — after all NPC builders are loaded at startup |
| `LoadedNPCEvent` | IEvent | no | setup/main | `BuilderManager.onBuilderAdded()` — per NPC builder as it is added |

---

## Singleplayer Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `SingleplayerRequestAccessEvent` | IEvent | no | FJP / varies | `SingleplayerModule` — first dispatch in `CompletableFuture.thenAccept()` (FJP), second dispatch inline |

---

## i18n Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `GenerateDefaultLanguageEvent` | IEvent | no | command thread | `GenerateI18nCommand` — admin command to regenerate default translation files |
| `MessagesUpdated` | IEvent | no | varies | `I18nModule` — fired when translations are added/updated dynamically |

---

## Asset Loading Events (GlobalEventBus)

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `LoadAssetEvent` | IEvent | no | main | `HytaleServer` boot — plugins add asset loaders here; has `failed()` to signal load errors |
| `AssetPackRegisterEvent` | IEvent | no | main / varies | `AssetModule.registerPack()` — under `ASSET_LOCK.writeLock()` |
| `AssetPackUnregisterEvent` | IEvent | no | main / varies | `AssetModule.unregisterPack()` — under `ASSET_LOCK.writeLock()` |
| `SendCommonAssetsEvent` | **IAsyncEvent** | no | **Netty** | `SetupPacketHandler` — fired when client requests common assets during connection setup |

---

## Asset Store Events (GlobalEventBus)

Fired by `AssetStore` / `AssetRegistry` during asset loading and hot-reload.

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `AssetsEvent<K, T>` | IEvent | no | — | Abstract base class |
| `LoadedAssetsEvent<K, T>` | IEvent | no | setup/FJP | `AssetStore` — after assets are loaded or hot-reloaded |
| `RemovedAssetsEvent<K, T>` | IEvent | no | setup/FJP | `AssetStore` — when assets are removed or replaced |
| `GenerateAssetsEvent<K, T>` | IProcessedEvent | no | setup/FJP | `AssetStore` — allows plugins to programmatically generate assets; `IProcessedEvent`, not `IEvent` |
| `AssetStoreEvent<K>` | IEvent | no | — | Abstract base class for store registration events |
| `RegisterAssetStoreEvent` | IEvent | no | setup/main | `AssetRegistry` — when a new `AssetStore` is registered |
| `RemoveAssetStoreEvent` | IEvent | no | setup/main | `AssetRegistry` — when an `AssetStore` is unregistered |

---

## Asset Monitor Events (GlobalEventBus)

Fired by file-watcher threads when asset files change on disk (hot-reload).

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `AssetMonitorEvent<T>` | IEvent | no | — | Abstract base class |
| `AssetStoreMonitorEvent` | IEvent | no | file watcher | `HytaleAssetStore` — when watched asset files change |
| `CommonAssetMonitorEvent` | IEvent | no | file watcher | `CommonAssetModule` — when common (shared) asset files change |

---

## World Gen Events (GlobalEventBus)

Fired during world generation asset loading at startup.

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `ModifyEvent<T>` | IEvent | no | setup/main | Interface; dispatched from world gen JSON loaders (cave types, containers, layers, etc.) — lets plugins modify world gen data |

---

## Asset Editor Events (GlobalEventBus)

Internal events for the in-game asset editor tool. Not intended for regular plugins.

| Event | Type | Cancellable | Thread | Notes |
|---|---|---|---|---|
| `EditorClientEvent<K>` | IEvent | no | — | Abstract base class |
| `AssetEditorActivateButtonEvent` | IEvent | no | Netty | Editor client activates a UI button |
| `AssetEditorAssetCreatedEvent` | IEvent | no | Netty | New asset created in the editor |
| `AssetEditorClientDisconnectEvent` | IEvent | no | Netty | Editor client disconnects |
| `AssetEditorSelectAssetEvent` | IEvent | no | Netty | Editor client selects an asset |
| `AssetEditorUpdateWeatherPreviewLockEvent` | IEvent | no | Netty | Weather preview lock toggled |
| `AssetEditorFetchAutoCompleteDataEvent` | **IAsyncEvent** | no | Netty | Editor requests autocomplete data |
| `AssetEditorRequestDataSetEvent` | **IAsyncEvent** | no | Netty | Editor requests a data set |

---

## Summary for pyTale

### Off-WorldThread synchronous events (the hard case)

These `IEvent`s fire outside the WorldThread and need special routing in pyTale:

| Event | Thread | Has `getWorld()`? |
|---|---|---|
| `PlayerSetupConnectEvent` | Netty | no — player not yet in a world |
| `PlayerSetupDisconnectEvent` | Netty | no |
| `PlayerConnectEvent` | FJP | no (sets target world via `setWorld()`) |
| `PlayerDisconnectEvent` | varies | no |
| `AddPlayerToWorldEvent` | FJP | **yes** |
| `AddWorldEvent` | FJP | **yes** (it IS the world being created) |
| `RemoveWorldEvent` | main / WorldThread | yes |
| `AllWorldsLoadedEvent` | main / FJP | no |
| `BootEvent` / `ShutdownEvent` / `PrepareUniverseEvent` | main | no |
| `PluginSetupEvent` | setup | no |
| `LoadAssetEvent` | main | no |
| `AssetPackRegisterEvent` / `AssetPackUnregisterEvent` | main/varies | no |
| `AllNPCsLoadedEvent` / `LoadedNPCEvent` | setup/main | no |
| `SingleplayerRequestAccessEvent` | FJP / varies | no |
| `WorldPathChangedEvent` | FJP | no (path belongs to world, but no `getWorld()`) |
| `RemoveWarpEvent` | command thread | no |
| `ReplaceWarpEvent` | FJP | no |
| `GenerateDefaultLanguageEvent` / `MessagesUpdated` | command/varies | no |
| `AssetStoreMonitorEvent` / `CommonAssetMonitorEvent` | file watcher | no |
| `LoadedAssetsEvent` / `RemovedAssetsEvent` | setup/FJP | no |

Events without `getWorld()` cannot be routed to a WorldContext → must run in GeneralContext.
Events with `getWorld()` could be routed to the appropriate WorldContext (requires locking),
but `AddWorldEvent` is special — the world exists but the WorldContext may not be initialized yet.

### Async events

`IAsyncEvent` events — handlers receive a `CompletableFuture`, not the event directly.
Require a separate bridge in pyTale:

| Event | Thread |
|---|---|
| `PlayerChatEvent` | Netty (dispatch) / FJP (handlers) |
| `SendCommonAssetsEvent` | Netty |
| `AssetEditorFetchAutoCompleteDataEvent` | Netty |
| `AssetEditorRequestDataSetEvent` | Netty |

### ECS events

Not reachable via `getEventRegistry().registerGlobal()`. Require registration through
`EntityEventSystem` / `EntityHolderEventSystem` — separate implementation track.
All ECS events fire on **WorldThread**.
