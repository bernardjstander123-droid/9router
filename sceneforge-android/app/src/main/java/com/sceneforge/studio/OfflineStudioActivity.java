package com.sceneforge.studio;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Offline WebGL editor. External SaaS applications never gain access to its native bridge. */
public final class OfflineStudioActivity extends Activity {
  private static final String LOCAL = "file:///android_asset/sceneforge/index.html";
  private static final int PICK_FILE = 481;
  private static final int MAX_BYTES = 8_000_000;
  private final ExecutorService io = Executors.newSingleThreadExecutor();
  private WebView web;
  private ValueCallback<Uri[]> picker;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(0xff0b0e1b);
    getWindow().setNavigationBarColor(0xff0b0e1b);
    web = new WebView(this);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setAllowFileAccess(true); // only packaged Android asset is loaded
    s.setAllowContentAccess(true); // SAF import via user-selected picker
    s.setAllowFileAccessFromFileURLs(false);
    s.setAllowUniversalAccessFromFileURLs(false);
    s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    web.setBackgroundColor(0xff090d18);
    web.addJavascriptInterface(new Bridge(), "SceneForgeNative");
    web.setWebViewClient(new WebViewClient() {
      @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
        if (!req.isForMainFrame()) return false;
        if (LOCAL.equals(req.getUrl().toString())) return false;
        // Never navigate the privileged WebView to a remote website.
        return true;
      }
    });
    web.setWebChromeClient(new WebChromeClient() {
      @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams params) {
        if (picker != null) picker.onReceiveValue(null);
        picker = cb;
        try {
          Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
          intent.addCategory(Intent.CATEGORY_OPENABLE);
          intent.setType("*/*");
          startActivityForResult(Intent.createChooser(intent, "Import SceneForge file"), PICK_FILE);
          return true;
        } catch (Exception ex) {
          picker = null;
          toast("No file picker available");
          return false;
        }
      }
    });
    setContentView(web);
    web.loadUrl(LOCAL);
  }

  private boolean isLocal() { return web != null && LOCAL.equals(web.getUrl()); }
  private void toast(String m) { runOnUiThread(() -> Toast.makeText(this,m,Toast.LENGTH_LONG).show()); }

  private final class Bridge {
    @JavascriptInterface public void openOnline() {
      if (!isLocal()) return;
      runOnUiThread(() -> startActivity(new Intent(OfflineStudioActivity.this, MainActivity.class)));
    }
    @JavascriptInterface public void openDesignApp(String target) {
      if (!isLocal()) return;
      final String url;
      if ("figma".equals(target)) url = "https://www.figma.com/files/";
      else if ("canva".equals(target)) url = "https://www.canva.com/";
      else return;
      runOnUiThread(() -> {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
        catch (Exception ex) { toast("No browser found"); }
      });
    }
    /** Save PNG, or open Android's share chooser. No credential or remote upload involved. */
    @JavascriptInterface public void exportPng(String dataUrl, boolean share) {
      if (!isLocal() || dataUrl == null || !dataUrl.startsWith("data:image/png;base64,")
          || dataUrl.length() > MAX_BYTES * 2) return;
      io.execute(() -> {
        Uri uri = null;
        try {
          byte[] bytes = Base64.decode(dataUrl.substring("data:image/png;base64,".length()), Base64.DEFAULT);
          if (bytes.length == 0 || bytes.length > MAX_BYTES) throw new IllegalArgumentException("Image size");
          String name = "SceneForge-" + System.currentTimeMillis() + ".png";
          if (Build.VERSION.SDK_INT >= 29) {
            ContentValues vals = new ContentValues();
            vals.put(MediaStore.Downloads.DISPLAY_NAME, name);
            vals.put(MediaStore.Downloads.MIME_TYPE, "image/png");
            vals.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/SceneForge");
            vals.put(MediaStore.Downloads.IS_PENDING, 1);
            uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, vals);
            if (uri == null) throw new IllegalStateException("Cannot create file");
            try (OutputStream stream = getContentResolver().openOutputStream(uri)) {
              if (stream == null) throw new IllegalStateException("Cannot write file");
              stream.write(bytes);
            }
            vals.clear();
            vals.put(MediaStore.Downloads.IS_PENDING, 0);
            getContentResolver().update(uri, vals, null, null);
          } else {
            File dir = new File(getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "SceneForge");
            if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Cannot create folder");
            File out = new File(dir, name);
            try (OutputStream stream = new FileOutputStream(out)) { stream.write(bytes); }
            // Android 8-9 uses app-private export; sharing is not supported without FileProvider.
            if (share) { toast("Saved in app Downloads; sharing needs Android 10+"); return; }
          }
          if (share && uri != null) {
            final Uri sharedUri = uri;
            runOnUiThread(() -> {
              Intent send = new Intent(Intent.ACTION_SEND);
              send.setType("image/png");
              send.putExtra(Intent.EXTRA_STREAM, sharedUri);
              send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
              try { startActivity(Intent.createChooser(send, "Send SceneForge frame to Canva or Figma")); }
              catch (Exception ex) { toast("Saved PNG; share chooser unavailable"); }
            });
          } else toast("PNG saved to Downloads/SceneForge");
        } catch (Exception ex) {
          if (uri != null && Build.VERSION.SDK_INT >= 29) {
            try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
          }
          toast("PNG export failed");
        }
      });
    }
  }

  @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    super.onActivityResult(requestCode, resultCode, data);
    if (requestCode == PICK_FILE && picker != null) {
      picker.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
      picker = null;
    }
  }
  @Override protected void onDestroy() {
    if (picker != null) { picker.onReceiveValue(null); picker = null; }
    if (web != null) { web.removeJavascriptInterface("SceneForgeNative"); web.destroy(); web = null; }
    io.shutdown();
    super.onDestroy();
  }
}
