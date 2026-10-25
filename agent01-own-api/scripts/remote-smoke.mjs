import assert from 'node:assert/strict';
const endpoint=process.env.AGENT01_REMOTE_TEST_URL||'https://agent01-own-api.vercel.app';
const key=process.env.AGENT01_API_KEY;
if(!key)throw new Error('Missing private test key in Vercel environment');
let r=await fetch(endpoint+'/health',{signal:AbortSignal.timeout(16000)});
console.log('AGENT01_REMOTE_HEALTH_HTTP',r.status);
assert.equal(r.status,200);
r=await fetch(endpoint+'/v1/models',{headers:{Authorization:'Bearer '+key},signal:AbortSignal.timeout(16000)});
console.log('AGENT01_REMOTE_MODELS_HTTP',r.status);
assert.equal(r.status,200);
r=await fetch(endpoint+'/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:'agent01-local',max_tokens:36,stream:false,messages:[{role:'user',content:'What is two plus two? Reply in one sentence.'}]}),signal:AbortSignal.timeout(175000)});
console.log('AGENT01_REMOTE_CHAT_HTTP',r.status);
if(!r.ok){console.log('AGENT01_REMOTE_CHAT_ERROR',(await r.text()).slice(0,300));throw new Error('End-to-end inference failed')}
const response=await r.json();
console.log('AGENT01_REMOTE_CHAT_CONTENT',String(response.choices?.[0]?.message?.content).slice(0,150));
assert.equal(response.object,'chat.completion');
assert.match(response.choices?.[0]?.message?.content||'',/\b(4|four)\b/i);
console.log('AGENT01_END_TO_END_API_VERIFIED');
