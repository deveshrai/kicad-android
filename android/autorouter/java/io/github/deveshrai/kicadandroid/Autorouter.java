// Runs the Freerouting autorouter inside the KiCad Android app.
//
// KiCad (C++) exports the board as a Specctra DSN file, calls route() on a worker thread, and
// polls the status getters while it runs.  When route() returns, KiCad imports the session file
// as one undoable step.  This class is also runnable on its own through app_process, for testing:
//
//   adb shell CLASSPATH=/data/local/tmp/autorouter.dex app_process / \
//       io.github.deveshrai.kicadandroid.Autorouter in.dsn out.ses [passes]
//
// SPDX-License-Identifier: GPL-3.0-or-later

package io.github.deveshrai.kicadandroid;

import app.freerouting.board.actions.ItemIdGenerator;
import app.freerouting.core.RoutingJob;
import app.freerouting.core.RoutingJobState;
import app.freerouting.core.StoppableThread;
import app.freerouting.core.scoring.BoardStatistics;
import app.freerouting.io.BoardReadResult;
import app.freerouting.management.HeadlessBoardManager;
import app.freerouting.autoroute.pipeline.RoutingPipeline;
import app.freerouting.settings.RouterSettings;
import app.freerouting.settings.SettingsMerger;
import app.freerouting.settings.sources.ApiSettings;
import app.freerouting.settings.sources.DefaultSettings;
import app.freerouting.settings.sources.DsnFileSettings;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;

public final class Autorouter {

  // Status, read by KiCad while route() runs.  Stage is one of: idle, loading, fanout, routing,
  // optimizing, saving, done, failed, cancelled.
  private static volatile String stage = "idle";
  private static volatile String message = "";
  private static volatile int pass;
  private static volatile int unrouted = -1;
  private static volatile int connections = -1;
  private static volatile int vias = -1;
  private static volatile int violations = -1;
  private static volatile float traceLengthMm = -1;
  private static volatile int snapshotSerial;
  private static volatile long startedAt;
  private static volatile Worker worker;

  // Options for the next route() call, set by KiCad with setOptions() just before it.
  private static volatile String[] onlyNets;
  private static volatile String[] inactiveLayers;
  private static volatile boolean routeEnabled = true;
  private static volatile int fanoutMode = -1;
  private static volatile int optimizerPasses = -1;
  private static volatile int viaCost = -1;

  private Autorouter() {}

  /**
   * Options for the next route() call.
   *
   * @param nets route (and optimize) only these nets, by name; empty for every net
   * @param offLayers copper layers (by name) the router must not route on
   * @param route false to skip routing and only optimize what is on the board
   * @param fanout 1 to fan out SMD pads before routing, 0 not to, -1 for Freerouting's default
   * @param passes optimizer passes, 0 or less for the default
   * @param vias the cost of a via, 0 or less for the default (higher: fewer vias)
   */
  public static void setOptions(
      String[] nets, String[] offLayers, boolean route, int fanout, int passes, int vias) {
    onlyNets = nets;
    inactiveLayers = offLayers;
    routeEnabled = route;
    fanoutMode = fanout;
    optimizerPasses = passes;
    viaCost = vias;
  }

  /** Pauses the running job; its threads wait in their next check. */
  public static void pause() {
    StoppableThread.setPaused(true);
  }

  public static void resume() {
    StoppableThread.setPaused(false);
  }

  public static boolean isPaused() {
    return StoppableThread.isPaused();
  }

  public static String getStage() {
    return stage;
  }

  public static String getMessage() {
    return message;
  }

  public static int getPass() {
    return pass;
  }

  public static int getUnrouted() {
    return unrouted;
  }

  public static int getConnections() {
    return connections;
  }

  public static int getVias() {
    return vias;
  }

  public static int getViolations() {
    return violations;
  }

  public static float getTraceLengthMm() {
    return traceLengthMm;
  }

  public static int getSnapshotSerial() {
    return snapshotSerial;
  }

  public static long getElapsedMs() {
    return startedAt == 0 ? 0 : System.currentTimeMillis() - startedAt;
  }

  /** Stops routing and goes on to optimize what is routed so far. */
  public static void stopRouting() {
    Worker w = worker;
    if (w != null) {
      w.requestStopAutoRouter();
    }
  }

  /** Stops everything.  route() still writes the session file with the work done so far. */
  public static void stopAll() {
    Worker w = worker;
    if (w != null) {
      w.requestStop();
    }
    StoppableThread.setPaused(false);
  }

  /**
   * Routes the board in {@code dsnPath} and writes the result to {@code sesPath}.  Blocks until
   * routing is done or stopped.
   *
   * @param maxPasses autorouter passes, 0 for no limit
   * @param optimize whether to run the optimizer after routing
   * @param threads worker threads, 0 for the number of cores minus one
   * @param snapshotPath if not empty, a session file written after each pass, so the caller can
   *     show progress on the board; getSnapshotSerial() goes up each time
   * @return an empty string on success, otherwise an error message
   */
  public static synchronized String route(
      String dsnPath,
      String sesPath,
      int maxPasses,
      boolean optimize,
      int threads,
      String snapshotPath) {
    stage = "loading";
    message = "Reading the board";
    pass = 0;
    unrouted = -1;
    connections = -1;
    vias = -1;
    violations = -1;
    traceLengthMm = -1;
    startedAt = System.currentTimeMillis();
    StoppableThread.setPaused(false);

    try {
      RoutingJob job = new RoutingJob();
      job.setInput(dsnPath);
      if (job.input == null || job.input.getData() == null) {
        return fail("Could not read " + dsnPath);
      }

      HeadlessBoardManager manager = new HeadlessBoardManager(job);
      BoardReadResult read =
          manager.loadFromSpecctraDsn(job.input.getData(), null, new ItemIdGenerator());
      if (!(read instanceof BoardReadResult.Success)
          && !(read instanceof BoardReadResult.OutlineMissing)) {
        return fail("Freerouting could not load the board: " + read);
      }
      job.board = manager.getRoutingBoard();
      if (job.board == null) {
        return fail("Freerouting could not load the board");
      }

      RouterSettings overrides = new RouterSettings();
      overrides.autorouter.maxPasses = Math.max(0, maxPasses);
      overrides.optimizer.enabled = optimize;
      if (threads > 0) {
        overrides.maxThreads = threads;
        overrides.autorouter.maxThreads = threads;
        overrides.optimizer.maxThreads = threads;
      }
      SettingsMerger merger = new SettingsMerger(new DefaultSettings());
      merger.addOrReplaceSources(
          new DsnFileSettings(job.input.getData(), job.input.getFilename()));
      merger.addOrReplaceSources(new ApiSettings(overrides));
      job.routerSettings = merger.merge();
      job.routerSettings.applyBoardSpecificOptimizations(job.board);
      job.routerSettings.applyNetClassExclusions(job.board);
      applyOptions(job);
      job.state = RoutingJobState.RUNNING;

      updateStatistics(job.board.getStatistics());

      Worker w = new Worker(job, snapshotPath);
      job.thread = w;
      worker = w;
      w.start();
      w.join();
      worker = null;

      if (w.failure != null) {
        return fail("Routing failed: " + w.failure);
      }

      stage = "saving";
      message = "Writing the routes";
      byte[] ses = sessionBytes(job);
      if (ses == null) {
        return fail("Could not write the session file");
      }
      Files.write(new File(sesPath).toPath(), ses);
      updateStatistics(job.board.getStatistics());
      stage = w.isStopRequested() ? "cancelled" : "done";
      message = "";
      return "";
    } catch (Throwable t) {
      worker = null;
      return fail(t.toString());
    } finally {
      StoppableThread.setPaused(false);
      app.freerouting.board.model.items.Item.onlyNets = null;
      setOptions(null, null, true, -1, -1, -1);
    }
  }

  private static void applyOptions(RoutingJob job) {
    String[] nets = onlyNets;
    app.freerouting.board.model.items.Item.onlyNets =
        nets != null && nets.length > 0 ? new java.util.HashSet<>(java.util.Arrays.asList(nets)) : null;

    String[] off = inactiveLayers;
    if (off != null) {
      java.util.Set<String> names = new java.util.HashSet<>(java.util.Arrays.asList(off));
      var layers = job.board.layerStructure.layers;
      for (int i = 0; i < layers.length; i++) {
        if (names.contains(layers[i].name)) {
          job.routerSettings.setLayerActive(i, false);
        }
      }
    }

    job.routerSettings.autorouter.enabled = routeEnabled;
    if (fanoutMode >= 0) {
      job.routerSettings.fanout.enabled = fanoutMode == 1;
    }
    if (optimizerPasses > 0) {
      job.routerSettings.optimizer.maxPasses = optimizerPasses;
    }
    if (viaCost > 0) {
      job.routerSettings.setViaCosts(viaCost);
    }
  }

  private static String fail(String why) {
    stage = "failed";
    message = why;
    System.out.println("Autorouter: " + why);
    return why;
  }

  private static byte[] sessionBytes(RoutingJob job) throws IOException {
    HeadlessBoardManager out = new HeadlessBoardManager(job);
    out.replaceRoutingBoard(job.board);
    try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
      String name = job.name != null ? job.name : "board";
      return out.saveAsSpecctraSessionSes(baos, name) ? baos.toByteArray() : null;
    }
  }

  private static void updateStatistics(BoardStatistics s) {
    if (s == null) {
      return;
    }
    if (s.connections != null) {
      if (s.connections.incompleteCount != null) {
        unrouted = s.connections.incompleteCount;
      }
      if (s.connections.maximumCount != null) {
        connections = s.connections.maximumCount;
      }
    }
    if (s.vias != null && s.vias.totalCount != null) {
      vias = s.vias.totalCount;
    }
    if (s.clearanceViolations != null && s.clearanceViolations.totalCount != null) {
      violations = s.clearanceViolations.totalCount;
    }
    if (s.traces != null && s.traces.totalLengthMm != null) {
      traceLengthMm = s.traces.totalLengthMm;
    }
  }

  private static final class Worker extends StoppableThread {
    private final RoutingJob job;
    private final String snapshotPath;
    private long lastSnapshot;
    volatile String failure;

    Worker(RoutingJob job, String snapshotPath) {
      this.job = job;
      this.snapshotPath = snapshotPath;
      setName("freerouting");
    }

    @Override
    protected void threadAction() {
      try {
        RoutingPipeline pipeline = RoutingPipeline.createForHeadless(job);
        pipeline.addBoardUpdatedEventListener(
            event -> {
              updateStatistics(event.getBoardStatistics());
              var counters = event.getRouterCounters();
              if (counters != null && counters.passCount != null) {
                pass = counters.passCount;
              }
              switch (job.stage) {
                case OPTIMIZATION -> stage = "optimizing";
                default -> stage = "routing";
              }
              if (counters != null && counters.phase != null) {
                message = counters.phase;
              }
              writeSnapshot();
            });
        stage = "routing";
        message = "";
        pipeline.run();
        job.state = isStopRequested() ? RoutingJobState.CANCELLED : RoutingJobState.COMPLETED;
      } catch (Throwable t) {
        failure = t.toString();
        t.printStackTrace(System.out);
        job.state = RoutingJobState.TERMINATED;
      }
    }

    // Runs on the routing thread between steps, so the board is not changing underneath it.
    private void writeSnapshot() {
      if (snapshotPath == null || snapshotPath.isEmpty()) {
        return;
      }
      long now = System.currentTimeMillis();
      if (now - lastSnapshot < 1500) {
        return;
      }
      lastSnapshot = now;
      try {
        byte[] ses = sessionBytes(job);
        if (ses == null) {
          return;
        }
        File tmp = new File(snapshotPath + ".tmp");
        try (FileOutputStream f = new FileOutputStream(tmp)) {
          f.write(ses);
        }
        if (tmp.renameTo(new File(snapshotPath))) {
          snapshotSerial++;
        }
      } catch (Throwable t) {
        System.out.println("Autorouter: snapshot failed: " + t);
      }
    }
  }

  /** For testing from adb: Autorouter in.dsn out.ses [passes]. */
  public static void main(String[] args) throws Exception {
    if (args.length < 2) {
      System.out.println("usage: Autorouter in.dsn out.ses [passes [optimize]]");
      System.exit(2);
    }
    int passes = args.length > 2 ? Integer.parseInt(args[2]) : 0;
    boolean optimize = args.length > 3 ? Boolean.parseBoolean(args[3]) : true;
    Thread progress =
        new Thread(
            () -> {
              while (true) {
                System.out.printf(
                    "%6.1fs %-10s pass %d  unrouted %d/%d  vias %d  violations %d  %.1f mm  %s%n",
                    getElapsedMs() / 1000.0,
                    stage,
                    pass,
                    unrouted,
                    connections,
                    vias,
                    violations,
                    traceLengthMm,
                    message);
                try {
                  Thread.sleep(1000);
                } catch (InterruptedException e) {
                  return;
                }
              }
            });
    progress.setDaemon(true);
    progress.start();
    String err = route(args[0], args[1], passes, optimize, 0, args[1] + ".snap");
    progress.interrupt();
    System.out.println(err.isEmpty() ? "OK " + stage : "ERROR " + err);
    System.out.printf(
        "unrouted %d/%d  vias %d  violations %d  %.1f mm  in %.1fs%n",
        unrouted, connections, vias, violations, traceLengthMm, getElapsedMs() / 1000.0);
    System.exit(err.isEmpty() ? 0 : 1);
  }
}
