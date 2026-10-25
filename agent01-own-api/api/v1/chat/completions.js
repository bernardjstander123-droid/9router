import {randomUUID} from 'node:crypto';
import {authorized,error,validateChat} from '../../../lib/security.js';
import {complete,MODEL_ID} from '../../../lib/model.js';
export default async function handler(req,res){
 res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='POST')return error(res,405,'method_not_allowed','Use POST with JSON');
 if(!authorized(req)){res.setHeader('WWW-Authenticate','Bearer realm="Agent01"');return error(res,401,'authentication_error','Valid Agent 01 API key required')}
 const contentType=String(req.headers['content-type']||'');
 if(!contentType.includes('application/json'))return error(res,415,'invalid_request_error','Content-Type must be application/json');
 const problem=validateChat(req.body);
 if(problem)return error(res,400,'invalid_request_error',problem);
 const body=req.body, messages=body.messages.map(m=>({role:m.role,content:m.content.trim()}));
 try{
  const answer=await complete(messages,body.max_tokens??128);
  return res.status(200).json({
    id:'chatcmpl-'+randomUUID(),object:'chat.completion',created:Math.floor(Date.now()/1000),
    model:MODEL_ID,choices:[{index:0,message:{role:'assistant',content:answer},finish_reason:'stop'}],
    usage:null,system_fingerprint:null
  });
 }catch(e){
   console.error('Agent 01 model failure',String(e?.message||e).slice(0,160));
   return error(res,503,'service_unavailable','Local inference temporarily unavailable');
 }
}