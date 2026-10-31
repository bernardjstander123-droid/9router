# SceneForge Studio Android v14 (debug wrapper)

This is a **native Android WebView wrapper for the live SceneForge website**. It does not embed an offline AI model, Cerebrium GPU, or native 3D engine. Internet and the owner's Hatchable sign-in are required. The wrapper is **not yet tested on a physical Samsung Galaxy A07**.

Web editor: https://sceneforge-studio.hatchable.site
Canva and Figma edit links open the phone's browser. The wrapper allows camera/video permission only for the trusted SceneForge origin.
Android System WebView provides the site's compositing and WebGL support where available. MediaStore attempts to save WebView-generated PNG, WebM or MP4 blob exports in Downloads/SceneForge. Actual playback and camera capture must be verified on the device.
Only supported MIME types, safe names and a 30 MB limit are accepted by the file-export bridge. The bridge has no filesystem-read or command-execution capability. The app disables cleartext requests and backup.

## Build
Requires Java 17, Android SDK 35, and Gradle 8.10.2.

```sh
cd sceneforge-android
gradle :app:assembleDebug
```

APK path: app/build/outputs/apk/debug/app-debug.apk

The GitHub Actions workflow builds the APK, checks its archive and Android signature, and uploads the debug APK as a workflow artifact. Debug signing is for sideload tests, not Google Play publication.
