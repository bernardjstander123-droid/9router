package com.motionstudio.standalone;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.*;
import android.view.*;
import android.widget.*;
import java.io.File;
public class MainActivity extends Activity {
 Studio view; TextView status;
 @Override public void onCreate(Bundle b){super.onCreate(b); LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setBackgroundColor(0xff10121c);status=new TextView(this);status.setTextColor(-1);status.setPadding(18,18,18,18);status.setText("MOTION STUDIO · Scene editor");root.addView(status);view=new Studio();root.addView(view,new LinearLayout.LayoutParams(-1,0,1));LinearLayout bar=new LinearLayout(this);for(String s:new String[]{"Play/Pause","Camera","Export MP4"}){Button btn=new Button(this);btn.setText(s);bar.addView(btn,new LinearLayout.LayoutParams(0,-2,1));btn.setOnClickListener(v->{if(s.equals("Play/Pause"))view.play=!view.play;else if(s.equals("Camera"))view.angle+=.5f;else {status.setText("Encoding MP4...");new Thread(()->{try{File f=new File(getExternalFilesDir(null),"motion_studio.mp4");Mp4Exporter.export(f,320,480,30,3);runOnUiThread(()->status.setText("MP4 saved: "+f.getAbsolutePath()+" ("+f.length()+" bytes)"));}catch(Exception e){runOnUiThread(()->status.setText("Export failed: "+e.getMessage()));}}).start();}});}root.addView(bar);setContentView(root);}
 class Studio extends View {Paint p=new Paint(3);float angle=0;boolean play=true;float down;Studio(){super(MainActivity.this);}protected void onDraw(Canvas c){super.onDraw(c);c.drawColor(0xff10121c);float cx=getWidth()/2f,cy=getHeight()/2f;float t=angle;for(int i=0;i<8;i++){p.setColor(0xff7b54c9);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);float a=(float)(i*Math.PI/4+t);c.drawLine(cx,cy,cx+(float)Math.cos(a)*getWidth()*.42f,cy+(float)Math.sin(a)*getWidth()*.42f,p);}p.setColor(0xffdbb5ff);p.setStyle(Paint.Style.FILL);c.drawCircle(cx,cy,28,p);p.setColor(-1);p.setTextSize(26);c.drawText("3D SCENE PREVIEW",20,42,p);if(play)angle+=.012f;postInvalidateDelayed(33);}public boolean onTouchEvent(android.view.MotionEvent e){if(e.getAction()==0){down=e.getX();return true;}if(e.getAction()==2){angle+=(e.getX()-down)/150;down=e.getX();invalidate();return true;}return true;}}
}
