import {pipeline, env} from '@huggingface/transformers';
env.cacheDir='/tmp/a01-local-model';
env.allowRemoteModels=true;
export const MODEL_ID='agent01-qwen2.5-1.5b';
export const MODEL_SOURCE='onnx-community/Qwen2.5-1.5B-Instruct';
const BOSS='You are Agent 01 Original Boss, a practical AI supervisor. Follow Superpowers methods: create a plan, define tests, debug carefully and verify results. Treat outputs as suggestions unless tools actually performed changes. Never invent app deployments, revenue, access or external integrations. Project tracks: SmartServe, OMEGA X, Share App, MDGx1, Shadowbound.';
let cached;
export async function complete(messages,maxTokens=128) {
  if(!cached) cached=pipeline('text-generation',MODEL_SOURCE,{dtype:'q4'}).catch(e=>{cached=null;throw e});
  const engine=await cached;
  const data=[{role:'system',content:BOSS},...messages];
  const out=await engine(data,{max_new_tokens:maxTokens,do_sample:false});
  const generated=out?.[0]?.generated_text;
  const content=Array.isArray(generated)?generated.at(-1)?.content:typeof generated==='string'?generated:null;
  if(typeof content!=='string'||!content.trim()) throw new Error('EMPTY_GENERATION');
  return content.trim();
}