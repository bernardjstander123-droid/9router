package com.realmforge.engine;
import android.app.Activity;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Button;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;
public class MainActivity extends Activity {
 private GLSurfaceView view; private NativeRenderer renderer=new NativeRenderer();
 @Override public void onCreate(Bundle b){super.onCreate(b);
 LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
 TextView title=new TextView(this);title.setText("RealmForge Cinema • Native GPU Preview");title.setTextSize(19);root.addView(title);
 view=new GLSurfaceView(this);view.setEGLContextClientVersion(3);
 view.setRenderer(new GLSurfaceView.Renderer(){long start=System.nanoTime();
 public void onSurfaceCreated(GL10 gl,EGLConfig config){renderer.initRenderer(720,1280,30,5f);}
 public void onSurfaceChanged(GL10 gl,int w,int h){android.opengl.GLES30.glViewport(0,0,w,h);}
 public void onDrawFrame(GL10 gl){float t=(System.nanoTime()-start)/1e9f;renderer.renderFrame((int)(t*30),t);}
 });root.addView(view,new LinearLayout.LayoutParams(-1,0,1));
 Button info=new Button(this);info.setText("GPU preview active • MP4/AI export not yet connected");info.setEnabled(false);root.addView(info);setContentView(root);}
 @Override protected void onPause(){super.onPause();view.onPause();}
 @Override protected void onResume(){super.onResume();if(view!=null)view.onResume();}
}
