// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only

// KiCad Android: a copy of Qt 6.12's QtWindow with two changes.
//
// 1. Window surfaces are always TextureViews.  Even with
//    QT_ANDROID_SURFACE_CONTAINER_TYPE=TextureView the native side asks for a SurfaceView for
//    Vulkan windows, and that sits behind the activity window where KiCad's other frames cover
//    it.  A TextureView is composited in the view hierarchy, and its Surface works for Vulkan.
//
// 2. Window decoration.  Android has no window manager for the windows inside an activity, so
//    a dialog was a bare rectangle: no frame, no title, and no way to move it.  The platform
//    plugin (patches/qtbase 0005) reports frame margins for dialogs and passes them here with
//    the title and the colours; this view is then larger than the window's client area by
//    those margins, draws a title strip and a border in them, and lays its children out
//    inside.  Dragging the title strip moves the window, and the cross closes it.
//
// scripts/build-kicad-apk.sh compiles this file and puts the classes over the ones in
// Qt6Android.jar.

package org.qtproject.qt.android;

import android.annotation.SuppressLint;
import android.app.ActionBar;
import android.app.Activity;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Insets;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.text.TextPaint;
import android.text.TextUtils;

import android.view.DisplayCutout;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.os.Build;

import java.util.HashMap;

@SuppressLint("ViewConstructor")
class QtWindow extends QtLayout implements QtSurfaceInterface {
    private View m_surfaceContainer;
    private View m_nativeView;
    private final HashMap<Integer, QtWindow> m_childWindows = new HashMap<>();
    private QtWindow m_parentWindow;
    private GestureDetector m_gestureDetector;
    private final QtEditText m_editText;
    private boolean m_editTextFocusInitialized = false;
    private final QtInputConnection.QtInputConnectionListener m_inputConnectionListener;
    private boolean m_firstSafeMarginsDelivered = false;
    private int m_actionBarHeight = -1;

    // Decoration: the margins around the client area, all 0 for a window without one
    private int m_decorTop = 0;
    private int m_decorSide = 0;
    private int m_decorTitleColor;
    private int m_decorTextColor;
    private int m_decorBorderColor;
    private boolean m_decorCloseButton = false;
    private String m_title = "";
    private Paint m_decorPaint;
    private TextPaint m_decorTextPaint;
    // The client geometry Qt asked for last, in the parent's coordinates
    private int m_clientX = 0;
    private int m_clientY = 0;
    private int m_clientWidth = -1;
    private int m_clientHeight = -1;
    private boolean m_hasGeometry = false;
    // The size fitInParent() last made smaller: if Qt asks for it again, the window keeps it
    private int m_shrunkFromWidth = -1;
    private int m_shrunkFromHeight = -1;
    // A press on the title strip: a drag moves the window, a tap on the cross closes it
    private boolean m_decorPressed = false;
    private boolean m_decorDragging = false;
    private boolean m_decorPressedOnClose = false;
    private boolean m_decorPressedOnTitle = false;
    private float m_decorPressRawX;
    private float m_decorPressRawY;
    private int m_decorPressClientX;
    private int m_decorPressClientY;

    private static native void decorationGeometry(int id, int x, int y, int w, int h);
    private static native void decorationClose(int id);
    private static native void setSurface(int windowId, Surface surface);
    private static native void safeAreaMarginsChanged(Insets insets, int id);
    static native void windowFocusChanged(boolean hasFocus, int id);
    static native void updateWindows();

    QtWindow(Context context, boolean isForeignWindow, QtWindow parentWindow,
                    QtInputConnection.QtInputConnectionListener listener)
    {
        super(context);
        setId(View.generateViewId());
        m_inputConnectionListener = listener;
        setParent(parentWindow);
        setFocusableInTouchMode(true);
        setDefaultFocusHighlightEnabled(false);
        setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);

        // Views are by default visible, but QWindows are not.
        // We should ideally pick up the actual QWindow state here,
        // but QWindowPrivate::setVisible() expects to control the
        // order of events tightly, so we need to wait for a call
        // to QAndroidPlatformWindow::setVisible().
        setVisible(false);

        if (!isForeignWindow && context instanceof Activity) {
            // TODO QTBUG-122552 - Service keyboard input not implemented
            m_editText = new QtEditText(context, listener);
            m_editText.setFocusable(false);
            m_editText.setFocusableInTouchMode(false);
            m_editText.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            LayoutParams layoutParams = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT);
            QtNative.runAction(() -> addView(m_editText, layoutParams));
        } else {
            m_editText = null;
        }

        QtNative.runAction(() -> {
            m_gestureDetector =
                new GestureDetector(context, new GestureDetector.SimpleOnGestureListener() {
                    @Override
                    public void onLongPress(MotionEvent event) {
                        // The event is already in client coordinates, see onTouchEvent()
                        QtInputDelegate.longPress(getId(), (int) event.getX(), (int) event.getY());
                    }
                });
            m_gestureDetector.setIsLongpressEnabled(true);
        });

        registerSafeAreaMarginsListener();
    }

    void registerSafeAreaMarginsListener()
    {
        if (!(getContext() instanceof QtActivityBase))
            return;

        setOnApplyWindowInsetsListener((view, insets) -> {
            WindowInsets windowInsets = view.onApplyWindowInsets(insets);
            reportSafeAreaMargins(windowInsets, getId());

            return windowInsets;
        });

        // If the window is attached, try to directly deliver root insets
        if (isAttachedToWindow()) {
            WindowInsets insets = getRootWindowInsets();
            if (insets != null) {
                getRootView().post(() -> reportSafeAreaMargins(insets, getId()));
                m_firstSafeMarginsDelivered = true;
            }
        } else { // Otherwise request it upon attachement
            addOnAttachStateChangeListener(new View.OnAttachStateChangeListener() {
                @Override
                public void onViewAttachedToWindow(View view) {
                    view.removeOnAttachStateChangeListener(this);
                    view.requestApplyInsets();
                }

                @Override
                public void onViewDetachedFromWindow(View view) {}
            });
        }

        // Further, tag into pre draw to deliver safe area margins early on
        if (!m_firstSafeMarginsDelivered) {
            ViewTreeObserver.OnPreDrawListener listener = new ViewTreeObserver.OnPreDrawListener() {
                @Override
                public boolean onPreDraw() {
                    if (isAttachedToWindow()) {
                        WindowInsets insets = getRootWindowInsets();
                        if (insets != null) {
                            getViewTreeObserver().removeOnPreDrawListener(this);
                            getRootView().post(() -> reportSafeAreaMargins(insets, getId()));
                            m_firstSafeMarginsDelivered = true;
                            return true;
                        }
                    }

                    requestApplyInsets();

                    return true;
                }
            };
            getViewTreeObserver().addOnPreDrawListener(listener);
        }

        addOnLayoutChangeListener((view, l, t, r, b, oldl, oldt, oldr, oldb) -> {
            WindowInsets insets = getRootWindowInsets();
            if (insets != null)
                getRootView().post(() -> reportSafeAreaMargins(insets, getId()));
        });
    }

    @SuppressWarnings("deprecation")
    Insets getSafeInsets(View view, WindowInsets insets)
    {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            int types = WindowInsets.Type.displayCutout() | WindowInsets.Type.systemBars();
            return insets.getInsets(types);
        }

        // Android R and older
        int left = insets.getSystemWindowInsetLeft();
        int top = insets.getSystemWindowInsetTop();
        int right = insets.getSystemWindowInsetRight();
        int bottom = insets.getSystemWindowInsetBottom();

        // Android 9 and 10 emulators don't seem to be able
        // to handle this, but let's have the logic here anyway
        DisplayCutout cutout = insets.getDisplayCutout();
        if (cutout != null) {
            left = Math.max(left, cutout.getSafeInsetLeft());
            top = Math.max(top, cutout.getSafeInsetTop());
            right = Math.max(right, cutout.getSafeInsetRight());
            bottom = Math.max(bottom, cutout.getSafeInsetBottom());
        }

        // If a theme supports an action bar, sometimes it even if it's hidden
        // the insets might report values including the bar's height, not entirely
        // sure whether it's due to a delay or a bug, either way ensure the top
        // margin doesn't include the action bar's height.
        ActionBar actionBar = ((Activity) getContext()).getActionBar();
        if (actionBar == null || !actionBar.isShowing()) {
            int topWithoutActionBar = top - actionBarHeight();
            if (topWithoutActionBar > 0)
                top = topWithoutActionBar;
        }

        return Insets.of(left, top, right, bottom);
    }

    private void reportSafeAreaMargins(WindowInsets insets, int id)
    {
        View rootView = getRootView();

        int[] rootLocation = new int[2];
        rootView.getLocationOnScreen(rootLocation);
        int rootX = rootLocation[0];
        int rootY = rootLocation[1];

        int[] windowLocation = new int[2];
        getLocationOnScreen(windowLocation);
        int windowX = windowLocation[0];
        int windowY = windowLocation[1];

        // Offset values of window from root
        int leftOffset = windowX - rootX;
        int topOffset = windowY - rootY;
        int rightOffset = (rootX + rootView.getWidth()) - (windowX + getWidth());
        int bottomOffset = (rootY + rootView.getHeight()) - (windowY + getHeight());

        // Find the remaining minimum safe margins
        Insets safeInsets = getSafeInsets(rootView, insets);
        int left = Math.max(0, Math.min(safeInsets.left, safeInsets.left - leftOffset));
        int top = Math.max(0, Math.min(safeInsets.top, safeInsets.top - topOffset));
        int right = Math.max(0, Math.min(safeInsets.right, safeInsets.right - rightOffset));
        int bottom = Math.max(0, Math.min(safeInsets.bottom, safeInsets.bottom - bottomOffset));

        safeAreaMarginsChanged(Insets.of(left, top, right, bottom), id);
    }

    private int actionBarHeight()
    {
        if (m_actionBarHeight == -1) {
            TypedArray ta = getContext().getTheme().obtainStyledAttributes(
                new int[] { android.R.attr.actionBarSize });
            try {
                m_actionBarHeight = ta.getDimensionPixelSize(0, 0);
            } finally {
                ta.recycle();
            }
        }
        return m_actionBarHeight;
    }

    @UsedFromNativeCode
    void setVisible(boolean visible) {
        QtNative.runAction(() -> setVisibility(visible ? View.VISIBLE : View.INVISIBLE));
    }

    @Override
    public void onSurfaceChanged(Surface surface)
    {
        setSurface(getId(), surface);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event)
    {
        // Enable focus for the edit text on first touch event to avoid
        // early QtInputConnection callbacks from blocking the UI thread.
        if (!m_editTextFocusInitialized) {
            m_editTextFocusInitialized = true;
            if (m_editText != null) {
                m_editText.setFocusable(true);
                m_editText.setFocusableInTouchMode(true);
            }
        }

        windowFocusChanged(true, getId());
        if (m_editText != null && m_inputConnectionListener != null)
            m_inputConnectionListener.onEditTextChanged(m_editText);

        if (hasDecoration()) {
            if (handleDecorationTouch(event))
                return true;
            // Qt counts from the corner of the client area
            event.offsetLocation(-m_decorSide, -m_decorTop);
        }

        QtInputDelegate.sendTouchEvent(event, getId());
        if (m_gestureDetector != null)
            m_gestureDetector.onTouchEvent(event);

        if (hasDecoration())
            event.offsetLocation(m_decorSide, m_decorTop);
        return true;
    }

    private boolean hasDecoration()
    {
        return m_decorTop > 0 || m_decorSide > 0;
    }

    // The place of the client area: Qt's text selection handles and its edit menu ask for the
    // window's place on the screen and add Qt's coordinates to it.
    @Override
    public void getLocationOnScreen(int[] outLocation)
    {
        super.getLocationOnScreen(outLocation);
        outLocation[0] += m_decorSide;
        outLocation[1] += m_decorTop;
    }

    private boolean inClientArea(float x, float y)
    {
        return x >= m_decorSide && x < getWidth() - m_decorSide
                && y >= m_decorTop && y < getHeight() - m_decorSide;
    }

    private boolean onCloseButton(float x, float y)
    {
        return m_decorCloseButton && y < m_decorTop && x >= getWidth() - m_decorSide - m_decorTop;
    }

    // Returns true for an event that belongs to the decoration and so is not one for Qt
    private boolean handleDecorationTouch(MotionEvent event)
    {
        final int action = event.getActionMasked();

        if (action == MotionEvent.ACTION_DOWN) {
            if (inClientArea(event.getX(), event.getY()))
                return false;

            m_decorPressed = true;
            m_decorDragging = false;
            m_decorPressedOnClose = onCloseButton(event.getX(), event.getY());
            // The border is too thin to mean anything but a slip of the finger
            m_decorPressedOnTitle = event.getY() < m_decorTop;
            m_decorPressRawX = event.getRawX();
            m_decorPressRawY = event.getRawY();
            m_decorPressClientX = m_clientX;
            m_decorPressClientY = m_clientY;
            return true;
        }

        if (!m_decorPressed)
            return false;

        final float dx = event.getRawX() - m_decorPressRawX;
        final float dy = event.getRawY() - m_decorPressRawY;

        switch (action) {
        case MotionEvent.ACTION_MOVE:
            if (!m_decorDragging) {
                final int slop = ViewConfiguration.get(getContext()).getScaledTouchSlop();
                if (m_decorPressedOnTitle && m_hasGeometry && m_clientWidth > 0
                        && (Math.abs(dx) > slop || Math.abs(dy) > slop)) {
                    m_decorDragging = true;
                }
            }
            if (m_decorDragging)
                moveClientTo(m_decorPressClientX + Math.round(dx),
                             m_decorPressClientY + Math.round(dy));
            break;
        case MotionEvent.ACTION_UP:
            m_decorPressed = false;
            if (m_decorDragging) {
                m_decorDragging = false;
                moveClientTo(m_decorPressClientX + Math.round(dx),
                             m_decorPressClientY + Math.round(dy));
                decorationGeometry(getId(), m_clientX, m_clientY, m_clientWidth, m_clientHeight);
            } else if (m_decorPressedOnClose && onCloseButton(event.getX(), event.getY())) {
                decorationClose(getId());
            }
            break;
        case MotionEvent.ACTION_CANCEL:
            m_decorPressed = false;
            if (m_decorDragging) {
                m_decorDragging = false;
                decorationGeometry(getId(), m_clientX, m_clientY, m_clientWidth, m_clientHeight);
            }
            break;
        default:
            break;
        }
        return true;
    }

    // Moves the window while it is dragged.  Qt hears of the new position when the drag ends.
    private void moveClientTo(int x, int y)
    {
        if (!(getParent() instanceof View))
            return;

        final View parent = (View) getParent();
        final int outerWidth = m_clientWidth + 2 * m_decorSide;
        // Keep enough of the title strip inside the parent to take hold of again, and keep
        // it below the status bar
        final int grip = 3 * m_decorTop;
        int minOuterY = 0;
        final WindowInsets insets = getRootWindowInsets();
        if (insets != null) {
            int[] parentLocation = new int[2];
            parent.getLocationInWindow(parentLocation);
            minOuterY = Math.max(0, getSafeInsets(this, insets).top - parentLocation[1]);
        }

        int outerX = x - m_decorSide;
        int outerY = y - m_decorTop;
        outerX = Math.max(grip - outerWidth, Math.min(outerX, parent.getWidth() - grip));
        outerY = Math.max(minOuterY, Math.min(outerY, parent.getHeight() - m_decorTop));

        m_clientX = outerX + m_decorSide;
        m_clientY = outerY + m_decorTop;
        applyGeometry();
    }

    @Override
    public boolean onTrackballEvent(MotionEvent event)
    {
        QtInputDelegate.sendTrackballEvent(event, getId());
        return true;
    }

    @Override
    public boolean onGenericMotionEvent(MotionEvent event)
    {
        if (!hasDecoration())
            return QtInputDelegate.sendGenericMotionEvent(event, getId());

        // Hover and wheel events over the decoration are not for Qt
        if (!inClientArea(event.getX(), event.getY()))
            return true;

        event.offsetLocation(-m_decorSide, -m_decorTop);
        final boolean handled = QtInputDelegate.sendGenericMotionEvent(event, getId());
        event.offsetLocation(m_decorSide, m_decorTop);
        return handled;
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec)
    {
        if (!hasDecoration()) {
            super.onMeasure(widthMeasureSpec, heightMeasureSpec);
            return;
        }

        // The children share the client area
        final int width = MeasureSpec.getSize(widthMeasureSpec);
        final int height = MeasureSpec.getSize(heightMeasureSpec);
        measureChildren(
                MeasureSpec.makeMeasureSpec(Math.max(0, width - 2 * m_decorSide),
                                            MeasureSpec.getMode(widthMeasureSpec)),
                MeasureSpec.makeMeasureSpec(Math.max(0, height - m_decorTop - m_decorSide),
                                            MeasureSpec.getMode(heightMeasureSpec)));
        setMeasuredDimension(resolveSize(width, widthMeasureSpec),
                             resolveSize(height, heightMeasureSpec));
    }

    @Override
    protected void onLayout(boolean changed, int l, int t, int r, int b)
    {
        if (!hasDecoration()) {
            super.onLayout(changed, l, t, r, b);
            return;
        }

        final int clientWidth = Math.max(0, r - l - 2 * m_decorSide);
        final int clientHeight = Math.max(0, b - t - m_decorTop - m_decorSide);
        final int count = getChildCount();
        for (int i = 0; i < count; i++) {
            final View child = getChildAt(i);
            if (child.getVisibility() == GONE)
                continue;

            final QtLayout.LayoutParams lp = (QtLayout.LayoutParams) child.getLayoutParams();
            final int childLeft = m_decorSide + lp.x;
            final int childTop = m_decorTop + lp.y;
            final int childRight = (lp.width == ViewGroup.LayoutParams.MATCH_PARENT)
                    ? m_decorSide + clientWidth : childLeft + child.getMeasuredWidth();
            final int childBottom = (lp.height == ViewGroup.LayoutParams.MATCH_PARENT)
                    ? m_decorTop + clientHeight : childTop + child.getMeasuredHeight();
            child.layout(childLeft, childTop, childRight, childBottom);
        }
    }

    @Override
    protected void onDraw(Canvas canvas)
    {
        super.onDraw(canvas);

        if (!hasDecoration())
            return;

        final int width = getWidth();
        final int height = getHeight();

        if (m_decorPaint == null) {
            m_decorPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            m_decorTextPaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
            m_decorTextPaint.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
        }

        // The border, then the title strip inside it
        m_decorPaint.setStyle(Paint.Style.FILL);
        m_decorPaint.setColor(m_decorBorderColor);
        canvas.drawRect(0, 0, width, height, m_decorPaint);
        m_decorPaint.setColor(m_decorTitleColor);
        canvas.drawRect(m_decorSide, m_decorSide, width - m_decorSide, m_decorTop, m_decorPaint);

        final float stripHeight = m_decorTop - m_decorSide;
        final float stripCentre = m_decorSide + stripHeight / 2;
        float textRight = width - m_decorSide - stripHeight * 0.4f;

        if (m_decorCloseButton) {
            final float arm = stripHeight * 0.16f;
            final float crossX = width - m_decorSide - stripHeight / 2;
            m_decorPaint.setColor(m_decorTextColor);
            m_decorPaint.setStyle(Paint.Style.STROKE);
            m_decorPaint.setStrokeWidth(Math.max(2f, stripHeight * 0.05f));
            canvas.drawLine(crossX - arm, stripCentre - arm, crossX + arm, stripCentre + arm,
                            m_decorPaint);
            canvas.drawLine(crossX - arm, stripCentre + arm, crossX + arm, stripCentre - arm,
                            m_decorPaint);
            textRight = width - m_decorSide - stripHeight;
        }

        final float textLeft = m_decorSide + stripHeight * 0.4f;
        if (!m_title.isEmpty() && textRight > textLeft) {
            m_decorTextPaint.setColor(m_decorTextColor);
            m_decorTextPaint.setTextSize(stripHeight * 0.44f);
            final CharSequence text = TextUtils.ellipsize(m_title, m_decorTextPaint,
                                                          textRight - textLeft,
                                                          TextUtils.TruncateAt.END);
            final Paint.FontMetrics metrics = m_decorTextPaint.getFontMetrics();
            canvas.drawText(text, 0, text.length(), textLeft,
                            stripCentre - (metrics.ascent + metrics.descent) / 2,
                            m_decorTextPaint);
        }
    }

    // The margins around the client area: top for the title strip and the border above it,
    // side for the border at the left, right and bottom.  All 0 takes the decoration away.
    @UsedFromNativeCode
    void setDecoration(final int top, final int side, final int titleColor, final int textColor,
                       final int borderColor, final boolean closeButton)
    {
        QtNative.runAction(() -> {
            m_decorTop = top;
            m_decorSide = side;
            m_decorTitleColor = titleColor;
            m_decorTextColor = textColor;
            m_decorBorderColor = borderColor;
            m_decorCloseButton = closeButton;
            m_decorPressed = false;
            m_decorDragging = false;
            setWillNotDraw(!hasDecoration());
            applyGeometry();
            fitInParent();
            requestLayout();
            invalidate();
        });
    }

    @UsedFromNativeCode
    void setTitle(final String title)
    {
        QtNative.runAction(() -> {
            m_title = title == null ? "" : title;
            if (hasDecoration())
                invalidate();
        });
    }

    // Gives this view the client geometry plus the decoration around it
    private void applyGeometry()
    {
        if (!m_hasGeometry || !(getContext() instanceof QtActivityBase))
            return;

        if (m_clientWidth < 0 || m_clientHeight < 0 || !hasDecoration()) {
            setLayoutParams(new QtLayout.LayoutParams(m_clientWidth, m_clientHeight,
                                                      m_clientX, m_clientY));
        } else {
            setLayoutParams(new QtLayout.LayoutParams(m_clientWidth + 2 * m_decorSide,
                                                      m_clientHeight + m_decorTop + m_decorSide,
                                                      m_clientX - m_decorSide,
                                                      m_clientY - m_decorTop));
        }
    }

    @Override
    protected void onAttachedToWindow()
    {
        super.onAttachedToWindow();
        setOnDragListener(QtDragManager.getInstance());
        if (hasDecoration())
            post(this::fitInParent);
    }

    // Keeps a decorated window clear of the status bar and the navigation bar or taskbar, as a
    // window manager would: Qt places dialogs inside the screen, and on Android the screen
    // includes the system bars.  The window is moved, and if it is taller or wider than the
    // room, made smaller; Qt hears of the new geometry like of the end of a drag.
    private void fitInParent()
    {
        if (!hasDecoration() || !m_hasGeometry || m_clientWidth <= 0 || m_clientHeight <= 0
                || m_decorDragging || !(getParent() instanceof View)) {
            return;
        }

        final View parent = (View) getParent();
        final WindowInsets insets = getRootWindowInsets();
        if (insets == null || parent.getWidth() <= 0 || parent.getHeight() <= 0)
            return;

        int[] parentLocation = new int[2];
        parent.getLocationInWindow(parentLocation);
        final Insets bars = getSafeInsets(this, insets);
        final View root = getRootView();
        final int minX = Math.max(0, bars.left - parentLocation[0]);
        final int minY = Math.max(0, bars.top - parentLocation[1]);
        final int maxX = parent.getWidth() - Math.max(0, bars.right
                - (root.getWidth() - parentLocation[0] - parent.getWidth()));
        final int maxY = parent.getHeight() - Math.max(0, bars.bottom
                - (root.getHeight() - parentLocation[1] - parent.getHeight()));
        if (maxX - minX <= 2 * m_decorSide || maxY - minY <= m_decorTop + m_decorSide)
            return;

        int width = Math.min(m_clientWidth, maxX - minX - 2 * m_decorSide);
        int height = Math.min(m_clientHeight, maxY - minY - m_decorTop - m_decorSide);
        if (m_clientWidth == m_shrunkFromWidth && m_clientHeight == m_shrunkFromHeight) {
            // The app wants this size even so (a minimum size, say): don't fight it
            width = m_clientWidth;
            height = m_clientHeight;
        } else if (width != m_clientWidth || height != m_clientHeight) {
            m_shrunkFromWidth = m_clientWidth;
            m_shrunkFromHeight = m_clientHeight;
        }
        final int outerWidth = width + 2 * m_decorSide;
        final int outerHeight = height + m_decorTop + m_decorSide;
        int outerX = m_clientX - m_decorSide;
        int outerY = m_clientY - m_decorTop;
        outerX = Math.max(minX, Math.min(outerX, maxX - outerWidth));
        outerY = Math.max(minY, Math.min(outerY, maxY - outerHeight));

        final int x = outerX + m_decorSide;
        final int y = outerY + m_decorTop;
        if (x == m_clientX && y == m_clientY && width == m_clientWidth
                && height == m_clientHeight) {
            return;
        }

        m_clientX = x;
        m_clientY = y;
        m_clientWidth = width;
        m_clientHeight = height;
        applyGeometry();
        decorationGeometry(getId(), x, y, width, height);
    }

    @Override
    protected void onDetachedFromWindow()
    {
        QtDragManager.getInstance().onSourceWindowDetached(this);
        setOnDragListener(null);
        super.onDetachedFromWindow();
    }

    @UsedFromNativeCode
    void removeWindow()
    {
        if (m_parentWindow != null)
            m_parentWindow.removeChildWindow(getId());
    }

    @UsedFromNativeCode
    void createSurface(final boolean onTop,
                              final int imageDepth, final boolean isOpaque,
                              final int surfaceContainerType) // TODO constant for type
    {
        QtNative.runAction(()-> {
            if (m_surfaceContainer != null)
                removeView(m_surfaceContainer);

            // KiCad Android: always a TextureView, see the top of this file
            m_surfaceContainer = new QtTextureView(getContext(), QtWindow.this, isOpaque);
             m_surfaceContainer.setLayoutParams(new QtLayout.LayoutParams(
                                                        ViewGroup.LayoutParams.MATCH_PARENT,
                                                        ViewGroup.LayoutParams.MATCH_PARENT));
            // The surface container of this window will be added as the first of the stack.
            // All other views are stacked based on the order they are created.
            addView(m_surfaceContainer, 0);
        });
    }

    @UsedFromNativeCode
    void destroySurface()
    {
        QtNative.runAction(()-> {
            if (m_surfaceContainer != null) {
                removeView(m_surfaceContainer);
                m_surfaceContainer = null;
                }
        }, false);
    }

    @UsedFromNativeCode
    void setGeometry(final int x, final int y, final int w, final int h)
    {
        QtNative.runAction(()-> {
            m_clientX = x;
            m_clientY = y;
            m_clientWidth = w;
            m_clientHeight = h;
            m_hasGeometry = true;
            applyGeometry();
            fitInParent();
        });
    }

    void addChildWindow(QtWindow window)
    {
        QtNative.runAction(()-> {
            m_childWindows.put(window.getId(), window);
            addView(window, getChildCount());
        });
    }

    void removeChildWindow(int id)
    {
        QtNative.runAction(()-> {
            if (m_childWindows.containsKey(id))
                removeView(m_childWindows.remove(id));
        });
    }

    @UsedFromNativeCode
    void setNativeView(final View view)
    {
        QtNative.runAction(()-> {
            if (m_nativeView != null)
                removeView(m_nativeView);

            m_nativeView = view;
            m_nativeView.setLayoutParams(new QtLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                                                                   ViewGroup.LayoutParams.MATCH_PARENT));
            addView(m_nativeView);
        });
    }

    @UsedFromNativeCode
    void bringChildToFront(int id)
    {
        QtNative.runAction(()-> {
            View view = m_childWindows.get(id);
            if (view != null) {
                if (getChildCount() > 0)
                    moveChild(view, getChildCount() - 1);
            }
        });
    }

    @UsedFromNativeCode
    void bringChildToBack(int id) {
        QtNative.runAction(()-> {
            View view = m_childWindows.get(id);
            if (view != null) {
                moveChild(view, 0);
            }
        });
    }

    @UsedFromNativeCode
    void removeNativeView()
    {
        QtNative.runAction(()-> {
            if (m_nativeView != null) {
                removeView(m_nativeView);
                m_nativeView = null;
            }
        });
    }

    void setParent(QtWindow parentWindow)
    {
        if (m_parentWindow == parentWindow)
            return;

        if (m_parentWindow != null)
            m_parentWindow.removeChildWindow(getId());

        m_parentWindow = parentWindow;
        if (m_parentWindow != null)
            m_parentWindow.addChildWindow(this);
    }

    @UsedFromNativeCode
    void updateFocusedEditText()
    {
        if (m_editText != null && m_inputConnectionListener != null)
            m_inputConnectionListener.onEditTextChanged(m_editText);
    }
}
