import {timingSafeEqual} from 'node:crypto';
export function authorized(req){
  const key=process.env.AGENT01_API_KEY||'';
  const header=String(req.headers.authorization||'');
  const found=/^Bearer ([A-Za-z0-9_-]+)$/i.exec(header);
  const supplied=found?.[1]||'';
  if(!key||!supplied)return false;
  const a=Buffer.from(key,'utf8'),b=Buffer.from(supplied,'utf8');
  return a.length===b.length&&timingSafeEqual(a,b);
}
export function error(res,status,code,message){
  return res.status(status).json({error:{message,type:code,code}});
}
export function validateChat(body){
 if(!body||typeof body!=='object'||Array.isArray(body))return 'Invalid JSON object';
 if(body.stream===true)return 'Streaming is not supported by this CPU API; set stream=false';
 if(body.tools||body.tool_choice||body.functions)return 'Tool calling is not supported';
 if(body.n!==undefined&&body.n!==1)return 'Only n=1 is supported';
 if(body.model!==undefined&&body.model!=='agent01-qwen2.5-1.5b'&&body.model!=='onnx-community/Qwen2.5-1.5B-Instruct')return 'Unknown model';
 const messages=body.messages;
 if(!Array.isArray(messages)||messages.length<1||messages.length>12)return 'messages must be an array of 1–12 items';
 if(!['user','assistant','system'].includes(messages.at(-1)?.role)||messages.at(-1)?.role!=='user')return 'Last message must be a user message';
 let count=0;
 for(const msg of messages){
  if(!msg||typeof msg!=='object'||!['system','user','assistant'].includes(msg.role)||typeof msg.content!=='string'||!msg.content.trim())return 'Messages must have text content and role system, user, or assistant';
  count+=msg.content.length;
  if(count>3200)return 'Conversation exceeds 3,200 characters';
 }
 if(body.max_tokens!==undefined&&(!Number.isInteger(body.max_tokens)||body.max_tokens<1||body.max_tokens>220))return 'max_tokens must be 1–220';
 return null;
}