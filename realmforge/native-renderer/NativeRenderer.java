package com.realmforge.engine;
public final class NativeRenderer {
 static { System.loadLibrary("realmforge_native"); }
 public native boolean initRenderer(int width,int height);
 public native boolean drawFrame(float seconds);
 public native void release();
}
