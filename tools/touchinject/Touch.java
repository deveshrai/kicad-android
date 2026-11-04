// Multi-touch injector for testing KiCad's touch handling on a device (adb input is single-touch).
// Runs as the shell user through app_process, which may inject input (like scrcpy does).
//
//   Touch pinch CX CY FROM_SPAN TO_SPAN [STEPS]   two fingers, horizontal, spread or pinch
//   Touch pan X Y DX DY [STEPS]                   two fingers 200 px apart, moved together
//   Touch tap3 X Y                                three-finger tap around X,Y
//   Touch drag X Y DX DY [STEPS]                  one finger
//
// Coordinates are display pixels on the default display.  Build: tools/touchinject/build.sh
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.MotionEvent;

import java.lang.reflect.Method;

public class Touch {
    static Object sInputManager;
    static Method sInject;

    static void init() throws Exception {
        Class<?> cls;
        try {
            cls = Class.forName("android.hardware.input.InputManagerGlobal");
        } catch (ClassNotFoundException e) {
            cls = Class.forName("android.hardware.input.InputManager");
        }
        sInputManager = cls.getMethod("getInstance").invoke(null);
        sInject = cls.getMethod("injectInputEvent", InputEvent.class, int.class);
    }

    static long sDown;

    static void send(int action, float[][] pts) throws Exception {
        int n = pts.length;
        MotionEvent.PointerProperties[] props = new MotionEvent.PointerProperties[n];
        MotionEvent.PointerCoords[] coords = new MotionEvent.PointerCoords[n];
        for (int i = 0; i < n; i++) {
            props[i] = new MotionEvent.PointerProperties();
            props[i].id = i;
            props[i].toolType = MotionEvent.TOOL_TYPE_FINGER;
            coords[i] = new MotionEvent.PointerCoords();
            coords[i].x = pts[i][0];
            coords[i].y = pts[i][1];
            coords[i].pressure = 1f;
            coords[i].size = 0.1f;
        }
        MotionEvent ev = MotionEvent.obtain(sDown, SystemClock.uptimeMillis(), action, n, props,
                coords, 0, 0, 1f, 1f, 0, 0, InputDevice.SOURCE_TOUCHSCREEN, 0);
        sInject.invoke(sInputManager, ev, 2 /* wait for finish */);
        ev.recycle();
    }

    static int ptr(int action, int index) {
        return action | (index << MotionEvent.ACTION_POINTER_INDEX_SHIFT);
    }

    /** Put fingers down one by one at a[], move linearly to b[] in steps, lift them. */
    static void gesture(float[][] a, float[][] b, int steps, long stepMs) throws Exception {
        int n = a.length;
        sDown = SystemClock.uptimeMillis();
        for (int k = 1; k <= n; k++) {
            float[][] cur = new float[k][];
            System.arraycopy(a, 0, cur, 0, k);
            send(k == 1 ? MotionEvent.ACTION_DOWN : ptr(MotionEvent.ACTION_POINTER_DOWN, k - 1), cur);
            Thread.sleep(10);
        }
        float[][] cur = a;
        for (int s = 1; s <= steps; s++) {
            float t = (float) s / steps;
            cur = new float[n][2];
            for (int i = 0; i < n; i++) {
                cur[i][0] = a[i][0] + (b[i][0] - a[i][0]) * t;
                cur[i][1] = a[i][1] + (b[i][1] - a[i][1]) * t;
            }
            send(MotionEvent.ACTION_MOVE, cur);
            Thread.sleep(stepMs);
        }
        for (int k = n; k >= 1; k--) {
            float[][] c = new float[k][];
            System.arraycopy(cur, 0, c, 0, k);
            send(k == 1 ? MotionEvent.ACTION_UP : ptr(MotionEvent.ACTION_POINTER_UP, k - 1), c);
            Thread.sleep(10);
        }
    }

    public static void main(String[] args) throws Exception {
        init();
        String cmd = args[0];
        float x = Float.parseFloat(args[1]), y = Float.parseFloat(args[2]);
        switch (cmd) {
            case "pinch": {
                float s0 = Float.parseFloat(args[3]) / 2, s1 = Float.parseFloat(args[4]) / 2;
                int steps = args.length > 5 ? Integer.parseInt(args[5]) : 20;
                gesture(new float[][] {{x - s0, y}, {x + s0, y}},
                        new float[][] {{x - s1, y}, {x + s1, y}}, steps, 16);
                break;
            }
            case "pan": {
                float dx = Float.parseFloat(args[3]), dy = Float.parseFloat(args[4]);
                int steps = args.length > 5 ? Integer.parseInt(args[5]) : 20;
                gesture(new float[][] {{x - 100, y}, {x + 100, y}},
                        new float[][] {{x - 100 + dx, y + dy}, {x + 100 + dx, y + dy}}, steps, 16);
                break;
            }
            case "tap3":
                gesture(new float[][] {{x - 120, y}, {x, y - 60}, {x + 120, y}},
                        new float[][] {{x - 120, y}, {x, y - 60}, {x + 120, y}}, 2, 20);
                break;
            case "drag": {
                float dx = Float.parseFloat(args[3]), dy = Float.parseFloat(args[4]);
                int steps = args.length > 5 ? Integer.parseInt(args[5]) : 20;
                gesture(new float[][] {{x, y}}, new float[][] {{x + dx, y + dy}}, steps, 16);
                break;
            }
            default:
                System.err.println("unknown command " + cmd);
        }
    }
}
