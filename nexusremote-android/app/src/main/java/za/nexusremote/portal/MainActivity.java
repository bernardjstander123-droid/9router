package za.nexusremote.portal;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

public final class MainActivity extends Activity {
  private static final String HOME="https://nexusremote-operations.vercel.app/";
  private static final String HOST="nexusremote-operations.vercel.app";
  private static final int BACKGROUND=0xff0b1120;
  private static final int PANEL=0xff15243b;
  private static final int ACCENT=0xff6278ff;
  private static final int WHITE=0xffedf2ff;
  private final Handler ui=new Handler(Looper.getMainLooper());
  private WebView browser;
  private TextView status;
  private ProgressBar progress;
  private String pendingTab=null;

  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    getWindow().setStatusBarColor(BACKGROUND);
    getWindow().setNavigationBarColor(BACKGROUND);
    LinearLayout layout=new LinearLayout(this);
    layout.setOrientation(LinearLayout.VERTICAL);
    layout.setBackgroundColor(BACKGROUND);
    setContentView(layout);

    LinearLayout top=new LinearLayout(this);
    top.setOrientation(LinearLayout.VERTICAL);
    top.setPadding(dp(17),dp(15),dp(17),dp(9));
    top.setBackgroundColor(BACKGROUND);
    layout.addView(top,new LinearLayout.LayoutParams(-1,-2));

    TextView brand=new TextView(this);
    brand.setText("NEXUSREMOTE");
    brand.setTextColor(WHITE);
    brand.setTextSize(21);
    brand.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
    top.addView(brand);

    status=new TextView(this);
    status.setText("Checking hosted platform…");
    status.setTextColor(0xffa4c9e5);
    status.setTextSize(11);
    status.setMaxLines(2);
    top.addView(status);

    HorizontalScrollView scroller=new HorizontalScrollView(this);
    scroller.setHorizontalScrollBarEnabled(false);
    layout.addView(scroller,new LinearLayout.LayoutParams(-1,dp(51)));
    LinearLayout tabs=new LinearLayout(this);
    tabs.setOrientation(LinearLayout.HORIZONTAL);
    tabs.setPadding(dp(8),dp(3),dp(8),dp(3));
    scroller.addView(tabs);
    addTab(tabs,"HOME","home");
    addTab(tabs,"APPLY","apply");
    addTab(tabs,"WORKER","worker");
    addTab(tabs,"OWNER","owner");
    addUtility(tabs,"RELOAD",()->{if(browser!=null)browser.reload();checkHealth();});
    addUtility(tabs,"BROWSER",()->openExternal(HOME));

    progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
    progress.setMax(100);
    progress.setProgressTintList(android.content.res.ColorStateList.valueOf(ACCENT));
    layout.addView(progress,new LinearLayout.LayoutParams(-1,dp(3)));

    browser=new WebView(this);
    browser.setBackgroundColor(BACKGROUND);
    browser.setVerticalScrollBarEnabled(false);
    WebSettings settings=browser.getSettings();
    settings.setJavaScriptEnabled(true);
    settings.setDomStorageEnabled(true);
    settings.setAllowFileAccess(false);
    settings.setAllowContentAccess(false);
    settings.setJavaScriptCanOpenWindowsAutomatically(false);
    settings.setSupportMultipleWindows(false);
    settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    settings.setSaveFormData(false);
    CookieManager.getInstance().setAcceptCookie(true);
    CookieManager.getInstance().setAcceptThirdPartyCookies(browser,false);
    browser.setWebChromeClient(new WebChromeClient(){
      @Override public void onProgressChanged(WebView view,int p){progress.setProgress(p);progress.setVisibility(p>=100?View.GONE:View.VISIBLE);}
    });
    browser.setWebViewClient(new WebViewClient(){
      @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
        Uri uri=request.getUrl();
        if("https".equalsIgnoreCase(uri.getScheme())&&HOST.equalsIgnoreCase(uri.getHost()))return false;
        if("https".equalsIgnoreCase(uri.getScheme()))openExternal(uri.toString());
        return true;
      }
      @Override public void onPageFinished(WebView view,String url){
        if(url!=null&&url.startsWith(HOME)&&pendingTab!=null){
          String tab=pendingTab;pendingTab=null;invokeTab(tab);
        }
      }
      @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError err){
        if(request.isForMainFrame()) status.setText("Cannot reach NexusRemote. Check internet and tap RELOAD.");
      }
    });
    layout.addView(browser,new LinearLayout.LayoutParams(-1,0,1f));
    if(state!=null)browser.restoreState(state);
    else browser.loadUrl(HOME);
    checkHealth();
  }
  private void addTab(LinearLayout bar,String name,String id){
    Button b=makeButton(name,true);
    bar.addView(b,buttonParams());
    b.setOnClickListener(v->goToTab(id));
  }
  private void addUtility(LinearLayout bar,String name,Runnable run){
    Button b=makeButton(name,false);
    bar.addView(b,buttonParams());
    b.setOnClickListener(v->run.run());
  }
  private LinearLayout.LayoutParams buttonParams(){
    LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-2,dp(43));
    p.setMargins(dp(3),0,dp(3),0);
    return p;
  }
  private Button makeButton(String label,boolean primary){
    Button b=new Button(this);
    b.setText(label);
    b.setTextColor(WHITE);
    b.setAllCaps(false);
    b.setTextSize(11);
    b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
    b.setPadding(dp(10),0,dp(10),0);
    GradientDrawable bg=new GradientDrawable();
    bg.setColor(primary?PANEL:0xff223052);
    bg.setCornerRadius(dp(10));
    bg.setStroke(dp(1),primary?0xff3a4c74:0xff526b97);
    b.setBackground(bg);
    return b;
  }
  private void goToTab(String tab){
    if(browser==null)return;
    Uri uri=Uri.parse(browser.getUrl()==null?"":browser.getUrl());
    if(!HOST.equals(uri.getHost())){
      pendingTab=tab;
      browser.loadUrl(HOME);
    }else invokeTab(tab);
  }
  private void invokeTab(String tab){
    if(!("home".equals(tab)||"apply".equals(tab)||"worker".equals(tab)||"owner".equals(tab)))return;
    browser.evaluateJavascript("(function(){let b=document.querySelector('[data-tab=\\\""+tab+"\\\"]');if(b){b.click();return true}return false})()",null);
  }
  private void openExternal(String uri){
    try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(uri)));}catch(ActivityNotFoundException e){status.setText("No external browser is available.");}
  }
  private void checkHealth(){
    new Thread(()->{
      String detail;
      HttpURLConnection c=null;
      try{
        c=(HttpURLConnection)new URL(HOME+"api/health").openConnection();
        c.setConnectTimeout(8500);
        c.setReadTimeout(8500);
        c.setInstanceFollowRedirects(false);
        c.setRequestProperty("Accept","application/json");
        if(c.getResponseCode()!=200)throw new Exception("Unexpected server response");
        try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
          byte[] buf=new byte[2048];int n;
          while((n=in.read(buf))!=-1){out.write(buf,0,n);if(out.size()>16000)break;}
          JSONObject j=new JSONObject(out.toString("UTF-8"));
          String storage=j.optString("privateStorage","");
          boolean stripe=j.optBoolean("stripeWebhookActive",false);
          boolean wa=j.optBoolean("whatsappAlertsActive",false);
          boolean dialer=j.optBoolean("dialerConnected",false);
          detail="ONLINE · Storage "+storage+" · Stripe "+(stripe?"on":"not connected")+" · WhatsApp "+(wa?"on":"not connected")+" · Dialer "+(dialer?"on":"not connected");
        }
      }catch(Exception e){detail="Cannot verify service · check connection";}
      finally{if(c!=null)c.disconnect();}
      final String result=detail;ui.post(()->{if(!isFinishing())status.setText(result);});
    }).start();
  }
  private int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+.5f);}
  @Override protected void onSaveInstanceState(Bundle b){if(browser!=null)browser.saveState(b);super.onSaveInstanceState(b);}
  @Override public void onBackPressed(){if(browser!=null&&browser.canGoBack())browser.goBack();else super.onBackPressed();}
  @Override protected void onDestroy(){if(browser!=null){browser.loadUrl("about:blank");browser.stopLoading();browser.destroy();browser=null;}super.onDestroy();}
}