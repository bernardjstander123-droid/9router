# RealmForge Android Native Renderer
Standalone, non-destructive Android NDK/OpenGL ES 3 procedural renderer module.
Files are intentionally isolated from the existing apps.
Requires an active EGL ES3 context on the calling thread before initRenderer/drawFrame.
To produce MP4, connect drawFrame to a MediaCodec input Surface via EGL and drain encoded output into MediaMuxer. This module does not yet encode MP4 or create an APK.
No AI model inference, photorealistic synthesis, or CPU fallback is implemented.
Status: source committed; Android compilation and device testing pending.
