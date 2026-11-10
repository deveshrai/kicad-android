package io.github.deveshrai.kicadandroid;

import android.content.Context;
import android.content.Intent;

/**
 * KiCad's side of RouterService: starts a step and signals its process.  Called from C++
 * (libs/kiplatform/os/android/router_process.cpp) on KiCad's main thread.
 */
public final class RouterControl {
  private static final int SIGCONT = 18;
  private static final int SIGSTOP = 19;

  private RouterControl() {
  }

  /** Starts one step; returns an empty string, or why it could not start. */
  public static String start(Context ctx, String dir, String log, String title, String[] argv,
                             String[] env) {
    try {
      Intent intent = new Intent(ctx, RouterService.class);
      intent.putExtra(RouterService.EXTRA_ARGV, argv);
      intent.putExtra(RouterService.EXTRA_ENV, env);
      intent.putExtra(RouterService.EXTRA_DIR, dir);
      intent.putExtra(RouterService.EXTRA_LOG, log);
      intent.putExtra(RouterService.EXTRA_TITLE, title);
      ctx.startForegroundService(intent);
      return "";
    } catch (Exception e) {
      return e.toString();
    }
  }

  public static void pause(int pid) {
    android.os.Process.sendSignal(pid, SIGSTOP);
  }

  public static void resume(int pid) {
    android.os.Process.sendSignal(pid, SIGCONT);
  }

  /** Stops a step for good.  A paused process is resumed first so it can die. */
  public static void kill(int pid) {
    android.os.Process.sendSignal(pid, SIGCONT);
    android.os.Process.killProcess(pid);
  }
}
