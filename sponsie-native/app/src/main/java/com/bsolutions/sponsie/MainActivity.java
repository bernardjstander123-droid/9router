package com.bsolutions.sponsie;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.Locale;

public final class MainActivity extends Activity {
    private WebView web;
    private Store store;
    private static final String[] TYPES = {"website", "proposal", "research", "content", "data"};
    private static boolean allowed(String type) { for (String t: TYPES) if (t.equals(type)) return true; return false; }
    private static String safe(String s, int max) { if (s == null) return ""; String v = s.trim(); return v.length() > max ? v.substring(0, max) : v; }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xff090d24);
        getWindow().setNavigationBarColor(0xff090d24);
        store = new Store();
        web = new WebView(this);
        WebSettings cfg = web.getSettings();
        cfg.setJavaScriptEnabled(true);
        cfg.setDomStorageEnabled(false);
        cfg.setAllowFileAccess(false);
        cfg.setAllowContentAccess(false);
        cfg.setJavaScriptCanOpenWindowsAutomatically(false);
        cfg.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) { return true; }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) { return true; }
        });
        web.addJavascriptInterface(new Bridge(), "Sponsie");
        setContentView(web);
        try(InputStream input = getAssets().open("index.html")) {
            String html = new String(input.readAllBytes(), StandardCharsets.UTF_8);
            web.loadDataWithBaseURL("https://sponsie.invalid/", html, "text/html", "UTF-8", null);
        } catch(Exception e) {
            web.loadData("<h2>Unable to open dashboard</h2>", "text/html", "UTF-8");
        }
    }
    @Override public void onDestroy(){ if(web!=null){web.removeJavascriptInterface("Sponsie");web.destroy();} if(store!=null)store.close(); super.onDestroy(); }
    private final class Store extends SQLiteOpenHelper {
        Store(){super(MainActivity.this,"sponsie-native.db",null,1);}
        @Override public void onCreate(SQLiteDatabase d){
            d.execSQL("CREATE TABLE tasks(id TEXT PRIMARY KEY,type TEXT NOT NULL,title TEXT NOT NULL,brief TEXT NOT NULL,output TEXT NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL)");
            d.execSQL("CREATE TABLE activity(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,created INTEGER NOT NULL)");
        }
        @Override public void onUpgrade(SQLiteDatabase d,int oldV,int newV) { }
        synchronized void record(SQLiteDatabase d,String event){ ContentValues row=new ContentValues();row.put("event",event);row.put("created",System.currentTimeMillis());d.insertOrThrow("activity",null,row); }
        synchronized String create(String type,String title,String brief) throws Exception {
            if(!allowed(type))throw new IllegalArgumentException("Unsupported assignment type");
            title=safe(title,100); brief=safe(brief,5000);
            if(title.isEmpty()||brief.isEmpty())throw new IllegalArgumentException("Title and brief are required");
            String id=UUID.randomUUID().toString(); String output=generate(type,title,brief);
            SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{
                ContentValues row=new ContentValues();row.put("id",id);row.put("type",type);row.put("title",title);row.put("brief",brief);row.put("output",output);row.put("status","REVIEW_REQUIRED");row.put("created",System.currentTimeMillis());
                d.insertOrThrow("tasks",null,row);record(d,"Created "+type+" draft: "+title);d.setTransactionSuccessful();
            }finally{d.endTransaction();}return id;
        }
        synchronized String list() throws Exception {
            JSONArray out=new JSONArray();
            try(Cursor c=getReadableDatabase().rawQuery("SELECT id,type,title,brief,status,created FROM tasks ORDER BY created DESC LIMIT 200",null)){
                while(c.moveToNext()){JSONObject o=new JSONObject();o.put("id",c.getString(0));o.put("type",c.getString(1));o.put("title",c.getString(2));o.put("brief",c.getString(3));o.put("status",c.getString(4));o.put("created",c.getLong(5));out.put(o);}
            } return out.toString();
        }
        synchronized String output(String id){try(Cursor c=getReadableDatabase().rawQuery("SELECT output FROM tasks WHERE id=?",new String[]{id})){return c.moveToFirst()?c.getString(0):"";}}
        synchronized String taskTitle(String id){try(Cursor c=getReadableDatabase().rawQuery("SELECT title FROM tasks WHERE id=?",new String[]{id})){return c.moveToFirst()?c.getString(0):"";}}
        synchronized boolean decide(String id,String decision){
            if(!decision.equals("READY_FOR_MANUAL_DELIVERY")&&!decision.equals("REJECTED"))return false;
            SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{
                ContentValues cv=new ContentValues();cv.put("status",decision);
                int n=d.update("tasks",cv,"id=? AND status='REVIEW_REQUIRED'",new String[]{id});
                if(n==1){record(d,"Owner marked task "+id.substring(0,8)+" as "+decision);d.setTransactionSuccessful();return true;}
                return false;
            }finally{d.endTransaction();}
        }
        synchronized String logs()throws Exception{
            JSONArray out=new JSONArray();try(Cursor c=getReadableDatabase().rawQuery("SELECT event,created FROM activity ORDER BY id DESC LIMIT 50",null)){
                while(c.moveToNext()){JSONObject o=new JSONObject();o.put("event",c.getString(0));o.put("created",c.getLong(1));out.put(o);}
            }return out.toString();
        }
    }
    private final class Bridge {
        @JavascriptInterface public String list(){try{return store.list();}catch(Exception e){return "[]";}}
        @JavascriptInterface public String logs(){try{return store.logs();}catch(Exception e){return "[]";}}
        @JavascriptInterface public String create(String type,String title,String brief){
            try{return new JSONObject().put("ok",true).put("id",store.create(type,title,brief)).toString();}
            catch(Exception e){try{return new JSONObject().put("ok",false).put("error",safe(e.getMessage(),160)).toString();}catch(Exception ignored){return "{\"ok\":false}";}}
        }
        @JavascriptInterface public String output(String id){ return store.output(safe(id,80)); }
        @JavascriptInterface public void decide(String id, boolean approve){
            final String task=safe(id,80);final String title=store.taskTitle(task);if(title.isEmpty())return;
            runOnUiThread(()->new AlertDialog.Builder(MainActivity.this)
                .setTitle(approve?"Approve this draft?":"Reject this draft?")
                .setMessage("“"+title+"”\n\nApproval marks the output ready for your manual delivery. It does not contact the client or send anything.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton(approve?"Approve":"Reject",(d,w)->{
                    boolean ok=store.decide(task,approve?"READY_FOR_MANUAL_DELIVERY":"REJECTED");
                    web.evaluateJavascript("window.refreshSponsie && window.refreshSponsie()",null);
                    if(!ok)new AlertDialog.Builder(MainActivity.this).setMessage("This item was already reviewed.").setPositiveButton("OK",null).show();
                }).show());
        }
        @JavascriptInterface public void share(String id){
            String value=store.output(safe(id,80));if(value.isEmpty())return;
            runOnUiThread(()->{
                Intent i=new Intent(Intent.ACTION_SEND);i.setType("text/plain");i.putExtra(Intent.EXTRA_SUBJECT,store.taskTitle(id));i.putExtra(Intent.EXTRA_TEXT,value);
                startActivity(Intent.createChooser(i,"Export a draft manually"));
            });
        }
    }
    private static String esc(String s){return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("'","&#39;");}
    private static String generate(String type,String title,String brief){
        String t=esc(title),b=esc(brief);
        if(type.equals("website")){
            return "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>"+t+"</title><style>body{margin:0;background:#10162d;color:#fff;font:16px system-ui}header{background:linear-gradient(125deg,#582bc8,#1592ca);padding:64px 24px;text-align:center}h1{font-size:clamp(32px,6vw,62px)}main{max-width:800px;margin:45px auto;padding:20px}.cta{display:inline-block;border:1px solid #fff;border-radius:12px;padding:12px 20px}footer{color:#aab;text-align:center;padding:30px}</style><header><h1>"+t+"</h1><p>Client brief-based landing page draft</p><span class=\"cta\">Contact us</span></header><main><h2>About this project</h2><p>"+b.replace("\n","<br>")+"</p><h2>Next steps</h2><p>Replace placeholder details with client-approved copy before publishing. Contact links intentionally omitted.</p></main><footer>Original draft · Review before publishing</footer></html>";
        }
        if(type.equals("proposal")) return "PROPOSAL DRAFT — NOT SENT\n\nProject: "+title+"\n\nClient requirements:\n"+brief+"\n\nProposed approach:\n1. Confirm scope and acceptance criteria with the client.\n2. Produce a first deliverable.\n3. Review changes together.\n4. Package approved files.\n\nPricing: To be agreed with the client.\nDelivery timing: To be confirmed.\n\nNo commitment has been made.";
        if(type.equals("research")) return "RESEARCH BRIEF — SOURCE VERIFICATION REQUIRED\n\nTopic: "+title+"\nResearch request: "+brief+"\n\nEvidence ledger:\n- Source URL: [add credible URL]\n- Publisher and publication date: [verify]\n- Key finding: [verify]\n- Confidence: UNVERIFIED\n\nNo facts or citations have been invented.";
        if(type.equals("content")) return "ORIGINAL CONTENT DRAFT — REVIEW BEFORE POSTING\n\nCampaign: "+title+"\nSource brief: "+brief+"\n\nPost 1: Introducing our work and the problem we help solve.\nPost 2: What to expect from a well-scoped project.\nPost 3: Behind the scenes: research, creation and review.\n\nReplace generic wording with client-approved facts and brand voice. No posts sent.";
        return "DATA PROCESSING PLAN — NO DATASET PROVIDED\n\nAssignment: "+title+"\nBrief: "+brief+"\n\nSteps:\n1. Obtain client-authorized CSV.\n2. Preserve untouched original.\n3. Profile headers, missing values and duplicate keys.\n4. Produce cleaned dataset and an exceptions report.\n5. Verify results before delivery.\n\nNo rows were processed; attach a dataset through an approved workflow to perform real cleaning.";
    }
}
