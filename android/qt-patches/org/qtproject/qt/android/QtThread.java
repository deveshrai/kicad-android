// Replacement for Qt 6.12's org.qtproject.qt.android.QtThread (from Qt6Android.jar), with the
// same behaviour and API except that the Qt main-loop thread is created with a large stack.
//
// KiCad runs its interactive tools as coroutines on separate stacks and those call into Java.
// The Android runtime only accepts Java frames and JNI references inside the thread's own
// stack, so KiCad carves the coroutine stacks out of this thread's stack
// (kicad/common/android_coroutine_stacks.cpp).  The size is reserved address space; pages are
// only committed when touched.
//
// Licensed under the same terms as the Qt file it replaces (LGPL-3.0-only).

package org.qtproject.qt.android;

import java.util.ArrayList;
import java.util.concurrent.Semaphore;

class QtThread {
    /** Stack reserved for the Qt main loop, which also hosts KiCad's coroutine stacks. */
    private static final long MAIN_LOOP_STACK_SIZE = 512L * 1024 * 1024;

    private final ArrayList<Runnable> m_pendingRunnables = new ArrayList<Runnable>();
    private boolean m_exit = false;
    private final Thread m_qtThread;

    QtThread() {
        m_qtThread = new Thread(null, new Runnable() {
            @Override
            public void run() {
                while (!m_exit) {
                    try {
                        ArrayList<Runnable> pendingRunnables;
                        synchronized (m_qtThread) {
                            if (m_pendingRunnables.isEmpty())
                                m_qtThread.wait();
                            pendingRunnables = new ArrayList<Runnable>(m_pendingRunnables);
                            m_pendingRunnables.clear();
                        }
                        for (Runnable runnable : pendingRunnables)
                            runnable.run();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }, "qtMainLoopThread", MAIN_LOOP_STACK_SIZE);
        m_qtThread.start();
    }

    void post(Runnable runnable) {
        synchronized (m_qtThread) {
            m_pendingRunnables.add(runnable);
            m_qtThread.notify();
        }
    }

    void sleep(int milliseconds) {
        try {
            Thread.sleep(milliseconds);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    void run(final Runnable runnable) {
        final Semaphore sem = new Semaphore(0);
        synchronized (m_qtThread) {
            m_pendingRunnables.add(new Runnable() {
                @Override
                public void run() {
                    runnable.run();
                    sem.release();
                }
            });
            m_qtThread.notify();
        }
        try {
            sem.acquire();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    void exit() {
        m_exit = true;
        synchronized (m_qtThread) {
            m_qtThread.notify();
        }
        try {
            m_qtThread.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    boolean isAlive() {
        return m_qtThread.isAlive();
    }
}
