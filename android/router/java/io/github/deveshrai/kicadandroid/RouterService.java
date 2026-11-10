package io.github.deveshrai.kicadandroid;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Runs one Python program (a routing step of KiCadRoutingTools) in a process of its own
 * (android:process=":router"), so a crash or the router's memory use cannot take KiCad down.
 *
 * The step's work directory receives "pid" when the program starts and "exit" (its exit code)
 * when it ends; its output goes to the log file named in the intent.  KiCad pauses, resumes and
 * stops the step with signals to that pid (RouterControl).  Each step is a fresh process, so
 * Python starts clean every time.
 */
public class RouterService extends Service {
  static final String EXTRA_ARGV = "argv";
  static final String EXTRA_ENV = "env";
  static final String EXTRA_DIR = "dir";
  static final String EXTRA_LOG = "log";
  static final String EXTRA_TITLE = "title";

  private static final String CHANNEL = "autoroute";
  private static final int NOTIFICATION_ID = 0x4b52;   // "KR"

  private static native int runPython(String[] argv, String[] env, String logPath);

  private volatile boolean busy;

  @Override
  public IBinder onBind(Intent intent) {
    return null;
  }

  @Override
  public int onStartCommand(Intent intent, int flags, int startId) {
    if (intent == null || busy) {
      // A restart after the process died, or a second request while one runs: the caller
      // only ever starts one step at a time and waits for its "exit" file.
      return START_NOT_STICKY;
    }

    busy = true;
    final String[] argv = intent.getStringArrayExtra(EXTRA_ARGV);
    final String[] env = intent.getStringArrayExtra(EXTRA_ENV);
    final String dir = intent.getStringExtra(EXTRA_DIR);
    final String log = intent.getStringExtra(EXTRA_LOG);
    String title = intent.getStringExtra(EXTRA_TITLE);

    goForeground(title != null ? title : "Autorouting");

    Thread worker = new Thread(null, () -> {
      int code = 1;

      try {
        write(new File(dir, "pid"), Integer.toString(android.os.Process.myPid()));
        System.loadLibrary("krtrunner");
        code = runPython(argv, env, log);
      } catch (Throwable t) {
        try {
          write(new File(dir, "error"), t.toString());
        } catch (Exception ignored) {
        }
      }

      try {
        write(new File(dir, "exit"), Integer.toString(code));
      } catch (Exception ignored) {
      }

      // Python cannot be started twice in one process (numpy and friends do not survive a
      // re-initialisation), so the process ends with its step.
      stopForeground(STOP_FOREGROUND_REMOVE);
      stopSelf();
      System.exit(0);
    }, "router", 64L * 1024 * 1024);

    worker.start();
    return START_NOT_STICKY;
  }

  private void goForeground(String title) {
    NotificationManager nm = getSystemService(NotificationManager.class);

    if (nm.getNotificationChannel(CHANNEL) == null) {
      NotificationChannel ch = new NotificationChannel(CHANNEL, "Autorouting",
                                                       NotificationManager.IMPORTANCE_LOW);
      ch.setDescription("Shown while the autorouter works on a board.");
      nm.createNotificationChannel(ch);
    }

    Notification n = new Notification.Builder(this, CHANNEL)
        .setContentTitle(title)
        .setContentText("KiCad is routing the board.")
        .setSmallIcon(getApplicationInfo().icon)
        .setOngoing(true)
        .build();

    if (Build.VERSION.SDK_INT >= 34) {
      startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
    } else {
      startForeground(NOTIFICATION_ID, n);
    }
  }

  private static void write(File f, String text) throws Exception {
    File tmp = new File(f.getPath() + ".tmp");

    try (FileOutputStream out = new FileOutputStream(tmp)) {
      out.write(text.getBytes(StandardCharsets.UTF_8));
    }

    if (!tmp.renameTo(f)) {
      throw new Exception("cannot write " + f);
    }
  }
}
