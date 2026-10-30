package com.realmforge.studio;
import android.app.Activity;
import android.os.Bundle;
import android.widget.*;
import java.io.File;
public final class MainActivity extends Activity {
 private TextView status; private Button export;
 @Override public void onCreate(Bundle state){super.onCreate(state);
 LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(24,24,24,24);
 TextView title=new TextView(this);title.setText("RealmForge • 3D Studio");title.setTextSize(24);root.addView(title);
 status=new TextView(this);status.setText("Native OpenGL ES 3 geometry → H.264 MP4");root.addView(status);
 export=new Button(this);export.setText("Render 5-second 3D MP4");root.addView(export);setContentView(root);
 export.setOnClickListener(v->{export.setEnabled(false);status.setText("Rendering…");new Thread(()->{
 try {File out=new File(getExternalFilesDir(null),"realmforge-3d.mp4");new SceneVideoExporter().export(out,720,1280,30,5);
 runOnUiThread(()->status.setText("Saved: "+out.getAbsolutePath()));}
 catch(Exception e){runOnUiThread(()->status.setText("Render failed: "+e.getMessage()));}
 finally{runOnUiThread(()->export.setEnabled(true));}
 }).start();});}
}
